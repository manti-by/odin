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


def redact_secret(text: str) -> str:
    """Keep the OMDb API key out of log lines: request exceptions embed the full URL."""
    key = settings.OMDB_API_KEY
    return text.replace(key, "***") if key else text


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
    except (InvalidOperation, TypeError, ValueError):  # fmt: skip
        return None
    return rating if 0 <= rating <= 10 else None


def parse_genres(value: object) -> list[str]:
    return [genre.strip() for genre in str(value or "").split(",") if genre.strip() and genre.strip() != "N/A"]


def apply_metadata(video: Video, payload: dict) -> None:
    video.title_omdb = str(payload.get("Title") or "").strip()
    video.year = parse_year(payload.get("Year")) or video.year
    video.imdb_rating = parse_rating(payload.get("imdbRating"))
    video.description = "" if payload.get("Plot") in (None, "N/A") else str(payload["Plot"]).strip()
    video.genres = parse_genres(payload.get("Genre"))
    video.metadata_status = FetchStatus.FETCHED
    video.metadata_attempts += 1
    video.save(
        update_fields=(
            "title_omdb",
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
    logger.warning(f"{video.path}: {redact_secret(message)} (attempt {video.metadata_attempts})")
    return video.metadata_status


_CYRILLIC = "абвгдеёжзийклмнопрстуфхцчшщъыьэюя"  # noqa: RUF001 - transliteration source alphabet
_LATIN = (
    "a",
    "b",
    "v",
    "g",
    "d",
    "e",
    "e",
    "zh",
    "z",
    "i",
    "y",
    "k",
    "l",
    "m",
    "n",
    "o",
    "p",
    "r",
    "s",
    "t",
    "u",
    "f",
    "kh",
    "ts",
    "ch",
    "sh",
    "shch",
    "",
    "y",
    "",
    "e",
    "yu",
    "ya",
)
CYRILLIC_TO_LATIN = dict(zip(_CYRILLIC, _LATIN, strict=True))


def transliterate(text: str) -> str:
    """Romanize a Cyrillic title so OMDb can match catalog entries listed in Latin script."""
    result: list[str] = []
    for char in text:
        latin = CYRILLIC_TO_LATIN.get(char.lower(), char)
        result.append(latin.capitalize() if char.isupper() and latin else latin)
    return "".join(result)


def search_titles(video: Video) -> list[str]:
    """OMDb candidates: the translation first, then a transliteration of the file title.

    A literal translation is often not the catalog title (`Брат` -> `Brother`, while OMDb lists it
    as `Brat`), so a translated-title miss falls back to the transliteration instead of retiring the
    row as `NOT_FOUND`. The raw Cyrillic title is not queried because OMDb matches Latin titles.
    """
    candidates = (video.title_en, transliterate(video.title))
    return list(dict.fromkeys(title.strip() for title in candidates if title and title.strip()))


def fetch_metadata(video: Video) -> FetchStatus:
    """Look one video up by its best English title + year and cache the result on the row.

    Candidates come from `search_titles`: the MyMemory translation when present, otherwise (or after
    a miss) a transliteration of the file title, so a Latin title (or a translation failure) never
    blocks enrichment. Never retries a `FETCHED` row; transient errors stay retryable until
    `VIDEO_FETCH_MAX_ATTEMPTS`. A rejected API key is raised as `MetadataAuthError` because every
    further request in the batch would fail the same way and burn the remaining attempts.
    """
    if not is_configured():
        logger.warning("OMDB_API_KEY is not configured, skipping video metadata")
        return video.metadata_status
    candidates = search_titles(video)
    if not candidates:
        logger.info(f"{video.path}: no title to search, skipping OMDb lookup")
        return video.metadata_status
    if not has_quota():
        logger.warning(f"OMDb daily limit of {settings.VIDEO_OMDB_DAILY_LIMIT} requests reached")
        return video.metadata_status

    payload: dict | None = None
    exhausted_quota = False
    for title in candidates:
        if not has_quota():
            exhausted_quota = True
            logger.warning(f"OMDb daily limit of {settings.VIDEO_OMDB_DAILY_LIMIT} requests reached")
            break

        params: dict[str, str | int] = {
            "apikey": settings.OMDB_API_KEY,
            "t": title,
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
            body = response.json()
        except requests.HTTPError as exc:
            code = exc.response.status_code if exc.response is not None else None
            if code in (401, 403):
                raise MetadataAuthError(redact_secret(f"OMDb rejected the API key: {exc}")) from exc
            if code == 429 or (code is not None and 500 <= code < 600):
                # A rate-limit or outage is temporary; skip the row without burning an attempt.
                logger.warning(f"{video.path}: OMDb unavailable ({code}), retrying later")
                return video.metadata_status
            return record_failure(video, f"OMDb request failed: {exc}")
        except (requests.RequestException, ValueError) as exc:
            return record_failure(video, f"OMDb request failed: {exc}")

        if not isinstance(body, dict):
            return record_failure(video, "OMDb returned a non-object JSON body")
        if str(body.get("Response", "")).lower() == "true":
            payload = body
            break

    if payload is None:
        if exhausted_quota:
            # Quota ran out before every candidate was tried, so a miss is not final.
            return video.metadata_status
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
