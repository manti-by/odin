import logging
from unittest.mock import Mock

import pytest

from django.core.cache.backends.locmem import LocMemCache

from odin.apps.video.models import FetchStatus, Video
from odin.apps.video.services import translation
from odin.tests.factories import VideoFactory


def mymemory_payload(text: str = "Brother", status: int = 200) -> dict:
    return {"responseStatus": status, "responseData": {"translatedText": text}}


def mymemory_response(payload: dict | list | None = None) -> Mock:
    return Mock(json=lambda: payload or mymemory_payload(), raise_for_status=Mock())


@pytest.fixture
def local_cache(monkeypatch):
    # LocMemCache instances share one class-level dict, so clear it to isolate the quota counter.
    cache = LocMemCache("video-translation", {})
    cache.clear()
    monkeypatch.setattr(translation, "cache", cache)
    return cache


@pytest.fixture
def translation_settings(settings, local_cache):
    settings.VIDEO_MYMEMORY_URL = "https://api.mymemory.translated.net/get"
    settings.VIDEO_MYMEMORY_EMAIL = ""
    settings.VIDEO_MYMEMORY_DAILY_LIMIT = 5000
    settings.VIDEO_FETCH_MAX_ATTEMPTS = 3
    settings.VIDEO_SCAN_BATCH_SIZE = 5
    return settings


@pytest.mark.django_db
class TestFetchTranslation:
    def test_translation__applies_translation(self, translation_settings, monkeypatch):
        get = Mock(return_value=mymemory_response())
        monkeypatch.setattr(translation.requests, "get", get)
        video = VideoFactory(title="Брат", title_en="", translation_status=FetchStatus.PENDING)

        result = translation.fetch_translation(video)

        video.refresh_from_db()
        assert result == FetchStatus.FETCHED
        assert video.title_en == "Brother"
        assert video.translation_attempts == 1
        assert get.call_args.kwargs["params"] == {"q": "Брат", "langpair": "ru|en"}

    def test_translation__sends_the_optional_email(self, translation_settings, monkeypatch):
        translation_settings.VIDEO_MYMEMORY_EMAIL = "user@example.com"
        get = Mock(return_value=mymemory_response())
        monkeypatch.setattr(translation.requests, "get", get)
        video = VideoFactory(title="Брат", title_en="")

        translation.fetch_translation(video)

        assert get.call_args.kwargs["params"]["de"] == "user@example.com"

    def test_translation__network_error_is_transient(self, translation_settings, monkeypatch):
        error = translation.requests.ConnectionError("boom")
        monkeypatch.setattr(translation.requests, "get", Mock(side_effect=error))
        video = VideoFactory(title="Брат", title_en="", translation_status=FetchStatus.PENDING)

        result = translation.fetch_translation(video)

        video.refresh_from_db()
        assert result == FetchStatus.ERROR
        assert video.translation_attempts == 0
        assert video.metadata_status == FetchStatus.PENDING
        assert Video.objects.pending_translations().filter(pk=video.pk).exists()

    def test_translation__quota_warning_is_transient(self, translation_settings, monkeypatch):
        warning = "MYMEMORY WARNING: YOU USED ALL AVAILABLE FREE TRANSLATIONS FOR TODAY."
        monkeypatch.setattr(
            translation.requests, "get", Mock(return_value=mymemory_response(mymemory_payload(warning)))
        )
        video = VideoFactory(title="Брат", title_en="", translation_status=FetchStatus.PENDING)

        result = translation.fetch_translation(video)

        video.refresh_from_db()
        assert result == FetchStatus.ERROR
        assert video.translation_attempts == 0
        assert video.title_en == ""
        assert video.metadata_status == FetchStatus.PENDING
        assert translation.has_quota(1) is False

    def test_translation__real_quota_response_stops_the_day(self, translation_settings, monkeypatch):
        payload = {
            "responseStatus": 403,
            "quotaFinished": True,
            "responseDetails": "MYMEMORY WARNING: YOU USED ALL AVAILABLE FREE TRANSLATIONS FOR TODAY.",
            "responseData": {"translatedText": ""},
        }
        monkeypatch.setattr(translation.requests, "get", Mock(return_value=mymemory_response(payload)))
        video = VideoFactory(title="Брат", title_en="", translation_status=FetchStatus.PENDING)

        result = translation.fetch_translation(video)

        video.refresh_from_db()
        assert result == FetchStatus.ERROR
        assert video.translation_attempts == 0
        assert translation.has_quota(1) is False

    def test_translation__quota_without_text_stops_the_day(self, translation_settings, monkeypatch):
        payload = {"responseStatus": 200, "quotaFinished": True, "responseData": {"translatedText": ""}}
        monkeypatch.setattr(translation.requests, "get", Mock(return_value=mymemory_response(payload)))
        video = VideoFactory(title="Брат", title_en="", translation_status=FetchStatus.PENDING)

        result = translation.fetch_translation(video)

        video.refresh_from_db()
        assert result == FetchStatus.ERROR
        assert video.translation_attempts == 0
        assert translation.has_quota(1) is False

    def test_translation__does_not_log_the_email(self, translation_settings, monkeypatch, caplog):
        translation_settings.VIDEO_MYMEMORY_EMAIL = "user@example.com"
        error = translation.requests.HTTPError(
            "500 Server Error for url: https://api.mymemory.translated.net/get?q=Heat&de=user%40example.com"
        )
        error.response = Mock(status_code=500)
        monkeypatch.setattr(translation.requests, "get", Mock(side_effect=error))
        video = VideoFactory(title="Брат", title_en="", translation_status=FetchStatus.PENDING)

        caplog.set_level(logging.WARNING)
        translation.fetch_translation(video)

        assert "user@example.com" not in caplog.text
        assert "user%40example.com" not in caplog.text
        assert "***" in caplog.text

    def test_translation__non_quota_warning_does_not_exhaust_the_budget(self, translation_settings, monkeypatch):
        warning = "PLEASE SELECT TWO DISTINCT LANGUAGES"
        monkeypatch.setattr(
            translation.requests, "get", Mock(return_value=mymemory_response(mymemory_payload(warning)))
        )
        video = VideoFactory(title="Брат", title_en="", translation_status=FetchStatus.PENDING)

        result = translation.fetch_translation(video)

        video.refresh_from_db()
        assert result == FetchStatus.ERROR
        assert video.translation_attempts == 0
        assert translation.has_quota(1) is True
        assert translation.used_today() == 0

    def test_translation__transient_failure_does_not_consume_the_budget(self, translation_settings, monkeypatch):
        error = translation.requests.ConnectionError("boom")
        monkeypatch.setattr(translation.requests, "get", Mock(side_effect=error))
        video = VideoFactory(title="Брат", title_en="", translation_status=FetchStatus.PENDING)

        translation.fetch_translation(video)

        assert translation.used_today() == 0

    def test_translation__respects_the_daily_quota(self, translation_settings, monkeypatch):
        get = Mock(return_value=mymemory_response())
        monkeypatch.setattr(translation.requests, "get", get)
        translation_settings.VIDEO_MYMEMORY_DAILY_LIMIT = len("Брат")
        first = VideoFactory(title="Брат", title_en="", translation_status=FetchStatus.PENDING)
        VideoFactory(title="Сестра", title_en="", translation_status=FetchStatus.PENDING)

        processed = translation.process_pending_translations(limit=5)

        first.refresh_from_db()
        assert processed == 1
        assert get.call_count == 1
        assert first.translation_status == FetchStatus.FETCHED
        assert translation.used_today() == len("Брат")

    def test_translation__gives_up_after_max_attempts(self, translation_settings, monkeypatch):
        monkeypatch.setattr(translation.requests, "get", Mock(return_value=mymemory_response(mymemory_payload(""))))
        video = VideoFactory(title="Брат", title_en="", translation_attempts=2)

        result = translation.fetch_translation(video)

        video.refresh_from_db()
        assert result == FetchStatus.ERROR
        assert video.translation_attempts == 3
        assert video.metadata_status == FetchStatus.ERROR
        # A permanently failed translation is still eligible for OMDb via the transliteration.
        assert Video.objects.pending_metadata().filter(pk=video.pk).exists()

    def test_translation__empty_text_is_a_failure(self, translation_settings, monkeypatch):
        monkeypatch.setattr(translation.requests, "get", Mock(return_value=mymemory_response(mymemory_payload(""))))
        video = VideoFactory(title="Брат", title_en="")

        result = translation.fetch_translation(video)

        video.refresh_from_db()
        assert result == FetchStatus.ERROR
        assert video.translation_attempts == 1
        assert video.title_en == ""

    def test_translation__non_200_status_is_transient(self, translation_settings, monkeypatch):
        monkeypatch.setattr(
            translation.requests,
            "get",
            Mock(return_value=mymemory_response({"responseStatus": 403, "responseData": {}})),
        )
        video = VideoFactory(title="Брат", title_en="")

        result = translation.fetch_translation(video)

        video.refresh_from_db()
        assert result == FetchStatus.ERROR
        assert video.translation_attempts == 0

    def test_translation__non_object_body_is_transient(self, translation_settings, monkeypatch):
        monkeypatch.setattr(translation.requests, "get", Mock(return_value=mymemory_response(["not", "an", "object"])))
        video = VideoFactory(title="Брат", title_en="")

        result = translation.fetch_translation(video)

        video.refresh_from_db()
        assert result == FetchStatus.ERROR
        assert video.translation_attempts == 0

    def test_translation__skips_a_video_without_a_title(self, translation_settings, monkeypatch):
        get = Mock()
        monkeypatch.setattr(translation.requests, "get", get)
        video = VideoFactory(title="", title_en="", translation_status=FetchStatus.PENDING)

        assert translation.fetch_translation(video) == FetchStatus.PENDING
        get.assert_not_called()

    def test_translation__skips_without_a_url(self, settings, monkeypatch):
        settings.VIDEO_MYMEMORY_URL = ""
        get = Mock()
        monkeypatch.setattr(translation.requests, "get", get)
        video = VideoFactory(title="Брат", title_en="", translation_status=FetchStatus.PENDING)

        assert translation.fetch_translation(video) == FetchStatus.PENDING
        get.assert_not_called()


@pytest.mark.django_db
class TestProcessPendingTranslations:
    def test_process__only_pending_rows(self, translation_settings, monkeypatch):
        monkeypatch.setattr(translation.requests, "get", Mock(return_value=mymemory_response()))
        pending = VideoFactory(title="Брат", title_en="", translation_status=FetchStatus.PENDING)
        VideoFactory(title="Сестра", title_en="Sister", translation_status=FetchStatus.FETCHED)

        processed = translation.process_pending_translations()

        pending.refresh_from_db()
        assert processed == 1
        assert pending.translation_status == FetchStatus.FETCHED

    def test_process__honours_the_batch_limit(self, translation_settings, monkeypatch):
        monkeypatch.setattr(translation.requests, "get", Mock(return_value=mymemory_response()))
        VideoFactory.create_batch(5, title="Брат", title_en="", translation_status=FetchStatus.PENDING)

        assert translation.process_pending_translations(limit=2) == 2
        assert Video.objects.pending_translations().count() == 3

    def test_process__stops_when_the_daily_quota_runs_out(self, translation_settings, monkeypatch):
        monkeypatch.setattr(translation.requests, "get", Mock(return_value=mymemory_response()))
        translation_settings.VIDEO_MYMEMORY_DAILY_LIMIT = len("Брат")
        VideoFactory(title="Брат", title_en="", translation_status=FetchStatus.PENDING)
        second = VideoFactory(title="Сестра", title_en="", translation_status=FetchStatus.PENDING)

        processed = translation.process_pending_translations()

        second.refresh_from_db()
        assert processed == 1
        assert second.translation_attempts == 0
        assert second.translation_status == FetchStatus.PENDING

    def test_process__skips_a_row_at_max_attempts(self, translation_settings, monkeypatch):
        get = Mock(return_value=mymemory_response())
        monkeypatch.setattr(translation.requests, "get", get)
        VideoFactory(title="Брат", title_en="", translation_status=FetchStatus.ERROR, translation_attempts=3)

        assert translation.process_pending_translations() == 0
        get.assert_not_called()

    def test_process__no_url_skips_everything(self, settings, monkeypatch):
        settings.VIDEO_MYMEMORY_URL = ""
        get = Mock()
        monkeypatch.setattr(translation.requests, "get", get)
        VideoFactory(title="Брат", title_en="", translation_status=FetchStatus.PENDING)

        assert translation.process_pending_translations() == 0
        get.assert_not_called()

    def test_process__one_failure_does_not_stop_the_batch(self, translation_settings, monkeypatch):
        monkeypatch.setattr(translation.requests, "get", Mock(return_value=mymemory_response()))
        broken = VideoFactory(title="Брат", title_en="", translation_status=FetchStatus.PENDING)
        healthy = VideoFactory(title="Сестра", title_en="", translation_status=FetchStatus.PENDING)
        original = translation.fetch_translation

        def flaky(video):
            if video.pk == broken.pk:
                raise RuntimeError("MyMemory is down")
            return original(video)

        monkeypatch.setattr(translation, "fetch_translation", flaky)

        processed = translation.process_pending_translations()

        healthy.refresh_from_db()
        assert processed == 1
        assert healthy.translation_status == FetchStatus.FETCHED


def test_has_quota__is_false_at_the_limit(translation_settings, local_cache):
    translation_settings.VIDEO_MYMEMORY_DAILY_LIMIT = 10
    local_cache.set(translation.quota_key(), 9)
    assert translation.has_quota() is True
    local_cache.set(translation.quota_key(), 10)
    assert translation.has_quota() is False


def test_consume_quota__keeps_the_running_total_on_expiry(translation_settings, local_cache, monkeypatch):
    local_cache.set(translation.quota_key(), 10)
    monkeypatch.setattr(local_cache, "incr", Mock(side_effect=ValueError))

    translation.consume_quota(5)

    assert translation.used_today() == 15
