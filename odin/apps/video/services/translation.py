import logging
from urllib.parse import quote, quote_plus

import requests

from django.conf import settings
from django.core.cache import cache
from django.utils import timezone

from odin.apps.video.models import FetchStatus, Video


logger = logging.getLogger(__name__)

QUOTA_CACHE_KEY = "video:mymemory:characters"
QUOTA_TTL = 60 * 60 * 48

TRANSIENT_MARKERS = (
    "MYMEMORY WARNING",
    "YOU USED ALL AVAILABLE FREE TRANSLATIONS",
    "PLEASE SELECT TWO DISTINCT LANGUAGES",
)
# Only the real "budget spent" message ends the day; other warnings must not burn the whole budget.
QUOTA_MARKERS = ("YOU USED ALL AVAILABLE FREE TRANSLATIONS",)


def is_configured() -> bool:
    return bool(settings.VIDEO_MYMEMORY_URL)


def redact_secret(text: str) -> str:
    """Keep the configured MyMemory email out of log lines: request exceptions embed the URL."""
    email = settings.VIDEO_MYMEMORY_EMAIL
    if not email:
        return text
    for secret in {email, quote(email), quote_plus(email)}:
        text = text.replace(secret, "***")
    return text


def quota_key() -> str:
    return f"{QUOTA_CACHE_KEY}:{timezone.localdate():%Y-%m-%d}"


def used_today() -> int:
    return int(cache.get(quota_key()) or 0)


def has_quota(characters: int = 0) -> bool:
    """Keep the scanner inside MyMemory's anonymous character budget for the day."""
    used = used_today()
    limit = settings.VIDEO_MYMEMORY_DAILY_LIMIT
    return used < limit and used + characters <= limit


def consume_quota(characters: int) -> None:
    key = quota_key()
    if cache.add(key, characters, timeout=QUOTA_TTL):
        return
    try:
        cache.incr(key, characters)
    except ValueError:
        # The key expired between `add` and `incr`; keep the accumulated total, not just this call.
        cache.set(key, used_today() + characters, timeout=QUOTA_TTL)


def exhaust_quota() -> None:
    """Spend the day's budget after MyMemory reports the quota is already gone."""
    cache.set(quota_key(), settings.VIDEO_MYMEMORY_DAILY_LIMIT, timeout=QUOTA_TTL)


def parse_translation(payload: object) -> tuple[str | None, bool, bool]:
    """Return `(title_en, transient, quota)` from a MyMemory response body.

    `title_en` is `None` when the body carries no usable translation. `transient` marks failures
    that will likely self-heal (server hiccups, outages) so they do not consume the permanent
    attempt budget; `quota` additionally means the anonymous budget is spent and the phase should
    stop for the day. MyMemory reports an exhausted quota with a non-200 `responseStatus`, so the
    quota signal is read from `quotaFinished`/`responseDetails` before that status is checked.
    """
    if not isinstance(payload, dict):
        return None, True, False
    data = payload.get("responseData")
    text = str(data.get("translatedText") or "").strip() if isinstance(data, dict) else ""
    details = str(payload.get("responseDetails") or "")
    message = f"{text} {details}".upper()
    quota = str(payload.get("quotaFinished")).lower() == "true" or any(marker in message for marker in QUOTA_MARKERS)
    if str(payload.get("responseStatus")) != "200":
        return None, True, quota
    if not text:
        # A spent quota may arrive with no translated text; keep it transient so it ends the day
        # instead of being charged as a permanent failure.
        return None, quota, quota
    if any(marker in message for marker in TRANSIENT_MARKERS):
        return None, True, quota
    return text, False, False


def record_failure(video: Video, message: str, *, transient: bool = False) -> FetchStatus:
    """Record one translation failure and give up after `VIDEO_FETCH_MAX_ATTEMPTS`.

    A `transient` failure (timeout, outage, anonymous-quota exhaustion) is retried indefinitely: the
    scanner ticks every minute, so letting it consume the attempt budget would permanently kill the
    translation, and the metadata phase with it, after a few minutes of downtime. Only a real,
    repeatable failure (a response without any translation) counts towards the give-up threshold.
    """
    video.translation_status = FetchStatus.ERROR
    update_fields = ["translation_status", "updated_at"]
    if not transient:
        video.translation_attempts += 1
        update_fields.append("translation_attempts")
        if video.translation_attempts >= settings.VIDEO_FETCH_MAX_ATTEMPTS and video.metadata_status in (
            FetchStatus.PENDING,
            FetchStatus.ERROR,
        ):
            video.metadata_status = FetchStatus.ERROR
            update_fields.append("metadata_status")
    video.save(update_fields=tuple(update_fields))
    kind = "transient" if transient else "permanent"
    logger.warning(f"{video.path}: {redact_secret(message)} ({kind}, attempt {video.translation_attempts})")
    return video.translation_status


def fetch_translation(video: Video) -> FetchStatus:
    """Translate one Russian title to English and cache it on the row.

    MyMemory is anonymous and rate-limited. A permanent failure (a 200 response with no usable
    translation) is retried until `VIDEO_FETCH_MAX_ATTEMPTS`; a transient one (timeout, outage,
    anonymous-quota exhaustion) keeps the row retryable without burning the attempt budget. The
    metadata phase skips a row whose translation has not succeeded yet.
    """
    if not video.title:
        return video.translation_status
    if not is_configured():
        logger.warning("VIDEO_MYMEMORY_URL is not configured, skipping video translation")
        return video.translation_status
    if not has_quota(len(video.title)):
        logger.warning(f"MyMemory daily limit of {settings.VIDEO_MYMEMORY_DAILY_LIMIT} characters reached")
        return video.translation_status

    params: dict[str, str] = {"q": video.title, "langpair": "ru|en"}
    if settings.VIDEO_MYMEMORY_EMAIL:
        params["de"] = settings.VIDEO_MYMEMORY_EMAIL

    try:
        response = requests.get(settings.VIDEO_MYMEMORY_URL, params=params, timeout=settings.VIDEO_MYMEMORY_TIMEOUT)
        response.raise_for_status()
        payload = response.json()
    except requests.HTTPError as exc:
        if exc.response is not None and exc.response.status_code in (403, 429):
            exhaust_quota()
        return record_failure(video, f"translation request failed: {exc}", transient=True)
    except (requests.RequestException, ValueError) as exc:
        return record_failure(video, f"translation request failed: {exc}", transient=True)

    title_en, transient, quota = parse_translation(payload)
    if title_en is None:
        if quota:
            exhaust_quota()
        elif not transient:
            # The API answered and rejected the title, so the characters were spent.
            consume_quota(len(video.title))
        return record_failure(video, "MyMemory returned no usable translation", transient=transient)

    consume_quota(len(video.title))
    video.title_en = title_en
    video.translation_status = FetchStatus.FETCHED
    video.translation_attempts += 1
    video.save(update_fields=("title_en", "translation_status", "translation_attempts", "updated_at"))
    logger.info(f"{video.path}: translated {video.title!r} -> {title_en!r}")
    return video.translation_status


def process_pending_translations(limit: int | None = None) -> int:
    """Translate the next batch of pending titles, stopping early once the daily budget is gone."""
    limit = settings.VIDEO_SCAN_BATCH_SIZE if limit is None else limit
    if not is_configured():
        return 0

    pending = Video.objects.pending_translations().filter(translation_attempts__lt=settings.VIDEO_FETCH_MAX_ATTEMPTS)
    processed = 0
    for video in pending[:limit]:
        if not has_quota(len(video.title)):
            logger.warning(f"MyMemory daily limit of {settings.VIDEO_MYMEMORY_DAILY_LIMIT} characters reached")
            break
        try:
            fetch_translation(video)
        except Exception:
            logger.exception(f"Video translation failed for {video.path}")
            continue
        processed += 1
    return processed
