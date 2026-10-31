import logging
from decimal import Decimal, InvalidOperation

import requests

from django.conf import settings
from django.core.cache import cache
from django.utils import timezone

from odin.apps.video.models import FetchStatus, Video


logger = logging.getLogger(__name__)

QUOTA_CACHE_KEY = "video:omdb:requests"
QUOTA_TTL = 60 * 60 * 48


def is_configured() -> bool:
    return bool(settings.OMDB_API_KEY)


def quota_key() -> str:
    return f"{QUOTA_CACHE_KEY}:{timezone.localdate():%Y-%m-%d}"


def requests_today() -> int:
    return int(cache.get(quota_key()) or 0)


def has_quota() -> bool:
    """Keep the scanner under the OMDb free tier (1,000 requests/day)."""
    return requests_today() < settings.VIDEO_OMDB_DAILY_LIMIT


def consume_quota() -> None:
    key = quota_key()
    if cache.add(key, 1, timeout=QUOTA_TTL):
        return
    try:
        cache.incr(key)
    except ValueError:
        cache.set(key, 1, timeout=QUOTA_TTL)


def parse_year(value: object) -> int | None:
    text = str(value or "").strip()
    return int(text[:4]) if len(text) >= 4 and text[:4].isdigit() else None


def parse_rating(value: object) -> Decimal | None:
    try:
        rating = Decimal(str(value))
    except InvalidOperation, TypeError, ValueError:
        return None
    return rating if 0 <= rating <= 10 else None


def parse_genres(value: object) -> list[str]:
    return [genre.strip() for genre in str(value or "").split(",") if genre.strip() and genre.strip() != "N/A"]


def apply_metadata(video: Video, payload: dict) -> None:
    video.title = str(payload.get("Title") or video.title).strip()
    video.year = parse_year(payload.get("Year")) or video.year
    video.imdb_rating = parse_rating(payload.get("imdbRating"))
    video.description = "" if payload.get("Plot") in (None, "N/A") else str(payload["Plot"]).strip()
    video.genres = parse_genres(payload.get("Genre"))
    video.metadata_status = FetchStatus.FETCHED
    video.metadata_attempts += 1
    video.save(
        update_fields=(
            "title",
            "year",
            "imdb_rating",
            "description",
            "genres",
            "metadata_status",
            "metadata_attempts",
            "updated_at",
        )
    )


class MetadataAuthError(Exception):
    """Raised when OMDb rejects the API key; the whole batch has to stop."""


def record_failure(video: Video, message: str) -> FetchStatus:
    """Record one retryable metadata failure and give up after `VIDEO_FETCH_MAX_ATTEMPTS`."""
    video.metadata_attempts += 1
    if video.metadata_attempts >= settings.VIDEO_FETCH_MAX_ATTEMPTS:
        video.metadata_status = FetchStatus.NOT_FOUND
    else:
        video.metadata_status = FetchStatus.ERROR
    video.save(update_fields=("metadata_status", "metadata_attempts", "updated_at"))
    logger.warning(f"{video.path}: {message} (attempt {video.metadata_attempts})")
    return video.metadata_status


def fetch_metadata(video: Video) -> FetchStatus:
    """Look one video up by parsed title + year and cache the result on the row.

    Never retries a `FETCHED` row; a miss is final, while transient errors stay retryable until
    `VIDEO_FETCH_MAX_ATTEMPTS`. A rejected API key is raised as `MetadataAuthError` because every
    further request in the batch would fail the same way and burn the remaining attempts.
    """
    if not is_configured():
        logger.warning("OMDB_API_KEY is not configured, skipping video metadata")
        return video.metadata_status
    if not has_quota():
        logger.warning(f"OMDb daily limit of {settings.VIDEO_OMDB_DAILY_LIMIT} requests reached")
        return video.metadata_status

    params: dict[str, str | int] = {
        "apikey": settings.OMDB_API_KEY,
        "t": video.title,
        "type": "movie",
        "plot": "short",
        "r": "json",
    }
    if video.year:
        params["y"] = video.year

    consume_quota()
    try:
        response = requests.get(settings.OMDB_API_URL, params=params, timeout=settings.OMDB_TIMEOUT)
        response.raise_for_status()
        payload = response.json()
    except requests.HTTPError as exc:
        if exc.response is not None and exc.response.status_code in (401, 403):
            raise MetadataAuthError(f"OMDb rejected the API key: {exc}") from exc
        return record_failure(video, f"OMDb request failed: {exc}")
    except (requests.RequestException, ValueError) as exc:
        return record_failure(video, f"OMDb request failed: {exc}")

    if not isinstance(payload, dict):
        return record_failure(video, "OMDb returned a non-object JSON body")

    if str(payload.get("Response", "")).lower() != "true":
        video.metadata_status = FetchStatus.NOT_FOUND
        video.metadata_attempts += 1
        video.save(update_fields=("metadata_status", "metadata_attempts", "updated_at"))
        logger.info(f"{video.path}: OMDb has no match for {video.release_label}")
        return video.metadata_status

    apply_metadata(video, payload)
    logger.info(f"{video.path}: OMDb metadata fetched for {video.release_label}")
    return video.metadata_status


def process_pending_metadata(limit: int | None = None) -> int:
    """Fetch the next batch of pending rows, stopping early on quota or a rejected API key."""
    limit = settings.VIDEO_SCAN_BATCH_SIZE if limit is None else limit
    if not is_configured():
        return 0

    pending = Video.objects.pending_metadata().filter(metadata_attempts__lt=settings.VIDEO_FETCH_MAX_ATTEMPTS)
    processed = 0
    for video in pending[:limit]:
        if not has_quota():
            logger.warning(f"OMDb daily limit of {settings.VIDEO_OMDB_DAILY_LIMIT} requests reached")
            break
        try:
            fetch_metadata(video)
        except MetadataAuthError as exc:
            logger.error(f"Video metadata batch aborted: {exc}")
            break
        except Exception:
            logger.exception(f"Video metadata fetch failed for {video.path}")
            continue
        processed += 1
    return processed
