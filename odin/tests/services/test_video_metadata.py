from decimal import Decimal
from unittest.mock import Mock

import pytest

from django.core.cache.backends.locmem import LocMemCache

from odin.apps.video.models import FetchStatus, Video
from odin.apps.video.services import metadata
from odin.tests.factories import VideoFactory


def omdb_payload(**overrides) -> dict:
    payload = {
        "Response": "True",
        "Title": "Heat",
        "Year": "1995",
        "imdbRating": "8.3",
        "Plot": "A crew of thieves.",
        "Genre": "Crime, Drama",
    }
    payload.update(**overrides)
    return payload


def omdb_response(payload: dict | None = None) -> Mock:
    return Mock(json=lambda: payload or omdb_payload(), raise_for_status=Mock())


@pytest.fixture
def local_cache(monkeypatch):
    # LocMemCache instances share one class-level dict, so clear it to isolate the quota counter.
    cache = LocMemCache("video-metadata", {})
    cache.clear()
    monkeypatch.setattr(metadata, "cache", cache)
    return cache


@pytest.fixture
def omdb_settings(settings, local_cache):
    settings.OMDB_API_KEY = "test-key"
    settings.VIDEO_OMDB_DAILY_LIMIT = 900
    settings.VIDEO_FETCH_MAX_ATTEMPTS = 3
    return settings


@pytest.mark.django_db
class TestFetchMetadata:
    def test_fetch__applies_metadata(self, omdb_settings, monkeypatch):
        get = Mock(return_value=omdb_response())
        monkeypatch.setattr(metadata.requests, "get", get)
        video = VideoFactory(title="heat", year=1995)

        result = metadata.fetch_metadata(video)

        video.refresh_from_db()
        assert result == FetchStatus.FETCHED
        assert video.title == "Heat"
        assert video.year == 1995
        assert video.imdb_rating == Decimal("8.3")
        assert video.description == "A crew of thieves."
        assert video.genres == ["Crime", "Drama"]
        assert get.call_args.kwargs["params"]["t"] == "heat"

    def test_fetch__unknown_title_is_not_found(self, omdb_settings, monkeypatch):
        payload = {"Response": "False", "Error": "Movie not found!"}
        monkeypatch.setattr(metadata.requests, "get", Mock(return_value=omdb_response(payload)))
        video = VideoFactory()

        result = metadata.fetch_metadata(video)

        video.refresh_from_db()
        assert result == FetchStatus.NOT_FOUND
        assert video.metadata_attempts == 1
        assert video.imdb_rating is None

    def test_fetch__na_values_are_dropped(self, omdb_settings, monkeypatch):
        payload = omdb_payload(imdbRating="N/A", Plot="N/A", Genre="N/A", Year="1995-1996")
        monkeypatch.setattr(metadata.requests, "get", Mock(return_value=omdb_response(payload)))
        video = VideoFactory(year=1995)

        metadata.fetch_metadata(video)

        video.refresh_from_db()
        assert video.imdb_rating is None
        assert video.description == ""
        assert video.genres == []
        assert video.year == 1995

    def test_fetch__network_error_is_retryable(self, omdb_settings, monkeypatch):
        error = metadata.requests.ConnectionError("boom")
        monkeypatch.setattr(metadata.requests, "get", Mock(side_effect=error))
        video = VideoFactory()

        result = metadata.fetch_metadata(video)

        video.refresh_from_db()
        assert result == FetchStatus.ERROR
        assert video.metadata_attempts == 1
        assert Video.objects.pending_metadata().filter(pk=video.pk).exists()

    def test_fetch__gives_up_after_max_attempts(self, omdb_settings, monkeypatch):
        error = metadata.requests.ConnectionError("boom")
        monkeypatch.setattr(metadata.requests, "get", Mock(side_effect=error))
        video = VideoFactory(metadata_attempts=2)

        result = metadata.fetch_metadata(video)

        video.refresh_from_db()
        assert result == FetchStatus.NOT_FOUND
        assert video.metadata_attempts == 3
        assert not Video.objects.pending_metadata().filter(pk=video.pk).exists()

    def test_fetch__non_object_body_is_retryable(self, omdb_settings, monkeypatch):
        monkeypatch.setattr(metadata.requests, "get", Mock(return_value=omdb_response(["not", "an", "object"])))
        video = VideoFactory()

        result = metadata.fetch_metadata(video)

        video.refresh_from_db()
        assert result == FetchStatus.ERROR
        assert video.metadata_attempts == 1

    def test_fetch__rejected_api_key_is_batch_fatal(self, omdb_settings, monkeypatch):
        error = metadata.requests.HTTPError("401 Client Error")
        error.response = Mock(status_code=401)
        monkeypatch.setattr(metadata.requests, "get", Mock(side_effect=error))
        video = VideoFactory()

        with pytest.raises(metadata.MetadataAuthError):
            metadata.fetch_metadata(video)

        video.refresh_from_db()
        assert video.metadata_status == FetchStatus.PENDING
        assert video.metadata_attempts == 0

    def test_fetch__skips_without_api_key(self, settings, local_cache, monkeypatch):
        settings.OMDB_API_KEY = ""
        get = Mock()
        monkeypatch.setattr(metadata.requests, "get", get)
        video = VideoFactory()

        assert metadata.fetch_metadata(video) == FetchStatus.PENDING
        get.assert_not_called()

    def test_fetch__respects_daily_quota(self, omdb_settings, monkeypatch):
        get = Mock(return_value=omdb_response())
        monkeypatch.setattr(metadata.requests, "get", get)
        omdb_settings.VIDEO_OMDB_DAILY_LIMIT = 1

        metadata.fetch_metadata(VideoFactory())
        metadata.fetch_metadata(VideoFactory())

        assert get.call_count == 1
        assert metadata.requests_today() == 1


@pytest.mark.django_db
class TestProcessPendingMetadata:
    def test_process__only_pending_rows(self, omdb_settings, monkeypatch):
        monkeypatch.setattr(metadata.requests, "get", Mock(return_value=omdb_response()))
        pending = VideoFactory(metadata_status=FetchStatus.PENDING)
        VideoFactory(metadata_status=FetchStatus.FETCHED)

        processed = metadata.process_pending_metadata()

        pending.refresh_from_db()
        assert processed == 1
        assert pending.metadata_status == FetchStatus.FETCHED

    def test_process__honours_the_batch_limit(self, omdb_settings, monkeypatch):
        monkeypatch.setattr(metadata.requests, "get", Mock(return_value=omdb_response()))
        VideoFactory.create_batch(5)

        assert metadata.process_pending_metadata(limit=2) == 2
        assert Video.objects.pending_metadata().count() == 3

    def test_process__no_api_key_skips_everything(self, settings, local_cache, monkeypatch):
        settings.OMDB_API_KEY = ""
        get = Mock()
        monkeypatch.setattr(metadata.requests, "get", get)
        VideoFactory()

        assert metadata.process_pending_metadata() == 0
        get.assert_not_called()

    def test_process__stops_when_the_daily_quota_runs_out(self, omdb_settings, monkeypatch):
        monkeypatch.setattr(metadata.requests, "get", Mock(return_value=omdb_response()))
        omdb_settings.VIDEO_OMDB_DAILY_LIMIT = 1
        VideoFactory(title="A First Movie")
        second = VideoFactory(title="B Second Movie")

        processed = metadata.process_pending_metadata()

        second.refresh_from_db()
        assert processed == 1
        assert second.metadata_status == FetchStatus.PENDING
        assert second.metadata_attempts == 0

    def test_process__aborts_on_a_rejected_api_key(self, omdb_settings, monkeypatch):
        error = metadata.requests.HTTPError("403 Client Error")
        error.response = Mock(status_code=403)
        monkeypatch.setattr(metadata.requests, "get", Mock(side_effect=error))
        first = VideoFactory(title="A First Movie")
        second = VideoFactory(title="B Second Movie")

        processed = metadata.process_pending_metadata()

        first.refresh_from_db()
        second.refresh_from_db()
        assert processed == 0
        assert (first.metadata_attempts, second.metadata_attempts) == (0, 0)

    def test_process__one_failure_does_not_stop_the_batch(self, omdb_settings, monkeypatch):
        monkeypatch.setattr(metadata.requests, "get", Mock(return_value=omdb_response()))
        broken = VideoFactory(title="A Broken Movie")
        healthy = VideoFactory(title="B Healthy Movie")
        original = metadata.fetch_metadata

        def flaky(video):
            if video.pk == broken.pk:
                raise RuntimeError("OMDb is down")
            return original(video)

        monkeypatch.setattr(metadata, "fetch_metadata", flaky)

        processed = metadata.process_pending_metadata()

        healthy.refresh_from_db()
        assert processed == 1
        assert healthy.metadata_status == FetchStatus.FETCHED


@pytest.mark.parametrize(
    ("value", "expected"),
    (("8.3", Decimal("8.3")), ("10", Decimal("10")), ("N/A", None), ("", None), ("11", None), (None, None)),
)
def test_parse_rating(value, expected):
    assert metadata.parse_rating(value) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    (("1995", 1995), ("1995-1996", 1995), ("N/A", None), ("", None), (None, None)),
)
def test_parse_year(value, expected):
    assert metadata.parse_year(value) == expected
