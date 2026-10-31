import logging
import os
import re
from collections.abc import Iterator
from pathlib import Path

from django.conf import settings

from odin.apps.cinema.models import FetchStatus, Video


logger = logging.getLogger(__name__)

VIDEO_EXTENSIONS = frozenset({".avi", ".flv", ".m2ts", ".m4v", ".mkv", ".mov", ".mp4", ".ts", ".webm", ".wmv"})
FILENAME_PATTERN = re.compile(r"^(?P<title>.+?)\s*\((?P<year>\d{4})\)")


def parse_filename(filename: str) -> tuple[str, int | None]:
    """Split a `Movie Name (Year).ext` file name into its title and year.

    A name without the year suffix keeps the whole stem as the title so the scan never drops a
    file; the caller decides whether that is worth a warning.
    """
    stem = Path(filename).stem.strip()
    match = FILENAME_PATTERN.match(stem)
    if not match:
        return stem, None
    return match["title"].strip(), int(match["year"])


def get_media_dirs() -> tuple[Path, ...]:
    return tuple(Path(directory).expanduser().resolve() for directory in settings.CINEMA_MEDIA_DIRS if directory)


def is_within_media_dirs(path: Path) -> bool:
    """Guard against a symlink in a configured share pointing outside every media root.

    The stream endpoint is anonymous and nginx maps the internal URI straight onto the filesystem,
    so a row is only allowed when its resolved path stays under `CINEMA_MEDIA_DIRS`.
    """
    resolved = path.resolve()
    return any(resolved.is_relative_to(root) for root in get_media_dirs())


def iter_video_files(root: Path) -> Iterator[Path]:
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in VIDEO_EXTENSIONS:
            continue
        if any(part.startswith(".") for part in path.relative_to(root).parts):
            continue
        yield path


def sync_video(path: Path) -> tuple[Video, bool, bool] | None:
    """Persist one file, returning `(video, created, changed)` or `None` when it is rejected.

    The mtime doubles as the incremental cache: an unchanged available row is skipped without a
    write, so a scan over a large library only touches new and modified files.
    """
    resolved_path = path.resolve()
    if not is_within_media_dirs(resolved_path):
        logger.warning(f"Cinema scan skipped {path}: the resolved path is outside CINEMA_MEDIA_DIRS")
        return None

    stat = path.stat()
    resolved = str(resolved_path)
    video = Video.objects.filter(path=resolved).first()

    if video and video.mtime == stat.st_mtime and video.is_available:
        return video, False, False

    title, year = parse_filename(path.name)
    if year is None:
        logger.warning(f"Cinema scan could not parse a year from {path.name}")

    created = video is None
    if created:
        video = Video(path=resolved, title=title, year=year)

    video.filename = path.name
    video.mtime = stat.st_mtime
    video.size = stat.st_size
    video.is_available = True
    if video.metadata_status == FetchStatus.PENDING:
        video.title, video.year = title, year

    video.save()
    logger.info(f"{'Added' if created else 'Updated'} cinema video {video.path}")
    return video, created, True


def mark_missing(root: Path, seen: set[str]) -> int:
    """Flag every available row under `root` that the scan did not see this run."""
    prefix = f"{root.resolve()}{os.sep}"
    missing = Video.objects.filter(path__startswith=prefix, is_available=True).exclude(path__in=seen)
    count = 0
    for video in missing:
        video.is_available = False
        video.save(update_fields=("is_available", "updated_at"))
        logger.info(f"Cinema video is no longer on disk: {video.path}")
        count += 1
    return count


def scan_library() -> dict[str, int]:
    """Walk every configured media dir and reconcile the `Video` table with the disk.

    Each root and each file is isolated: an unreadable directory or a broken symlink logs and the
    scan keeps going. A root that yields no files at all is treated as an unmounted share and its
    rows are left alone, so an empty mount point never hides the whole library.
    """
    stats = {"found": 0, "created": 0, "updated": 0, "missing": 0}
    for root in get_media_dirs():
        if not root.is_dir():
            logger.warning(f"Cinema media dir is not available: {root}")
            continue

        seen: set[str] = set()
        for path in iter_video_files(root):
            try:
                result = sync_video(path)
            except OSError as exc:
                logger.error(f"Cinema scan failed for {path}: {exc}")
                continue
            except Exception:
                logger.exception(f"Cinema scan failed for {path}")
                continue
            if result is None:
                continue
            video, created, changed = result
            seen.add(video.path)
            stats["found"] += 1
            if created:
                stats["created"] += 1
            elif changed:
                stats["updated"] += 1

        if not seen:
            logger.warning(f"Cinema media dir is empty, skipping missing-file reconciliation: {root}")
            continue
        stats["missing"] += mark_missing(root, seen)

    logger.info(
        f"Cinema scan finished: {stats['found']} files ({stats['created']} new, "
        f"{stats['updated']} updated), {stats['missing']} missing"
    )
    return stats
