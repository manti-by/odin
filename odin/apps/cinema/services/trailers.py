import logging
import shutil
import subprocess  # nosec B404
import tempfile
from pathlib import Path

from django.conf import settings
from django.utils.text import slugify

from odin.apps.cinema.models import FetchStatus, Video


logger = logging.getLogger(__name__)


class TrailerDownloadError(Exception):
    """Raised when yt-dlp cannot produce a trailer file."""


def build_query(video: Video) -> str:
    return f"{video.title} {video.year} трейлер" if video.year else f"{video.title} трейлер"


def trailer_filename(video: Video) -> str:
    slug = slugify(video.title, allow_unicode=True)[:80] or "movie"
    year = f"-{video.year}" if video.year else ""
    return f"{video.pk}-{slug}{year}.mp4"


def trailers_dir() -> Path:
    return Path(settings.CINEMA_TRAILERS_DIR)


def get_trailer_path(video: Video) -> Path | None:
    return trailers_dir() / video.trailer if video.trailer else None


def fetch_trailer_file(query: str, target: Path) -> None:
    """Download the first YouTube search hit as a single MP4 into `target`.

    yt-dlp writes into a scratch dir next to the target and the file is moved into place only
    after a successful exit, so a killed download never leaves a half-written trailer behind.
    Only an MP4 candidate is accepted: the row stores an `.mp4` trailer and the stream endpoint
    reports it as `video/mp4`, so a webm/mkv fallback would be a lie.
    """
    command = [
        settings.CINEMA_YTDLP_BIN,
        # Ignore operator config (e.g. `--write-info-json`) so a sidecar never lands in the
        # scratch dir next to the trailer.
        "--ignore-config",
        "--no-playlist",
        "--no-warnings",
        "--quiet",
        "--no-progress",
        "--format",
        "best[ext=mp4]/bestvideo[ext=mp4]+bestaudio[ext=m4a]",
        "--merge-output-format",
        "mp4",
        "--max-filesize",
        settings.CINEMA_TRAILER_MAX_FILESIZE,
    ]
    if settings.YOUTUBE_PROXY:
        command.extend(("--proxy", settings.YOUTUBE_PROXY))

    with tempfile.TemporaryDirectory(dir=target.parent) as scratch:
        result = subprocess.run(  # nosec B603
            (*command, "--paths", scratch, "--output", "%(id)s.%(ext)s", f"ytsearch1:{query}"),
            capture_output=True,
            text=True,
            timeout=settings.CINEMA_TRAILER_TIMEOUT,
            check=False,
        )
        if result.returncode != 0:
            raise TrailerDownloadError(result.stderr.strip() or f"yt-dlp exited with {result.returncode}")

        files = [path for path in Path(scratch).iterdir() if path.is_file()]
        mp4_files = [path for path in files if path.suffix.lower() == ".mp4"]
        if len(mp4_files) != 1:
            suffixes = sorted({path.suffix for path in files})
            raise TrailerDownloadError(f"yt-dlp produced no single MP4 for {query}: {suffixes}")
        mp4_files[0].replace(target)


def mark_downloaded(video: Video, target: Path) -> FetchStatus:
    """Link an existing trailer file to the row and mark the download finished."""
    video.trailer = target.name
    video.trailer_status = FetchStatus.FETCHED
    video.trailer_attempts += 1
    video.save(update_fields=("trailer", "trailer_status", "trailer_attempts", "updated_at"))
    logger.info(f"{video.path}: trailer saved to {target}")
    return video.trailer_status


def record_failure(video: Video, message: str) -> FetchStatus:
    """Record one retryable trailer failure and give up after `CINEMA_FETCH_MAX_ATTEMPTS`."""
    video.trailer_attempts += 1
    if video.trailer_attempts >= settings.CINEMA_FETCH_MAX_ATTEMPTS:
        video.trailer_status = FetchStatus.NOT_FOUND
    else:
        video.trailer_status = FetchStatus.ERROR
    video.save(update_fields=("trailer_status", "trailer_attempts", "updated_at"))
    logger.warning(f"{video.path}: {message} (attempt {video.trailer_attempts})")
    return video.trailer_status


def download_trailer(video: Video) -> FetchStatus:
    """Download the Russian trailer once and link it to the row.

    An existing non-empty file is reused instead of re-downloaded, so a rescan or a retry after a
    crash never hits YouTube again.
    """
    if not shutil.which(settings.CINEMA_YTDLP_BIN):
        logger.error(f"yt-dlp binary is not available: {settings.CINEMA_YTDLP_BIN}")
        return video.trailer_status

    target = trailers_dir() / trailer_filename(video)
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.is_file() and target.stat().st_size > 0:
        return mark_downloaded(video, target)

    try:
        fetch_trailer_file(build_query(video), target)
    except (TrailerDownloadError, OSError, subprocess.SubprocessError) as exc:
        return record_failure(video, f"trailer download failed: {exc}")

    if not target.is_file() or target.stat().st_size == 0:
        return record_failure(video, "trailer download produced an empty file")
    return mark_downloaded(video, target)


def process_pending_trailers(limit: int | None = None) -> int:
    """Download the next batch of pending trailers, isolating per-video failures."""
    limit = settings.CINEMA_SCAN_BATCH_SIZE if limit is None else limit
    pending = Video.objects.pending_trailers().filter(trailer_attempts__lt=settings.CINEMA_FETCH_MAX_ATTEMPTS)
    processed = 0
    for video in pending[:limit]:
        try:
            download_trailer(video)
        except Exception:
            logger.exception(f"Cinema trailer download failed for {video.path}")
            continue
        processed += 1
    return processed
