from pathlib import Path

import pytest

from odin.apps.cinema.models import FetchStatus, Video
from odin.apps.cinema.services import trailers
from odin.apps.cinema.services.trailers import (
    TrailerDownloadError,
    build_query,
    download_trailer,
    process_pending_trailers,
    trailer_filename,
)
from odin.tests.factories import VideoFactory


@pytest.fixture
def trailer_settings(tmp_path, settings, monkeypatch):
    settings.CINEMA_TRAILERS_DIR = str(tmp_path)
    settings.CINEMA_FETCH_MAX_ATTEMPTS = 3
    settings.CINEMA_SCAN_BATCH_SIZE = 5
    settings.YOUTUBE_PROXY = ""
    monkeypatch.setattr(trailers.shutil, "which", lambda binary: f"/usr/bin/{binary}")
    return settings


def write_trailer(query: str, target: Path) -> None:
    target.write_bytes(b"mp4")


def raise_download_error(query: str, target: Path) -> None:
    raise TrailerDownloadError("yt-dlp failed")


def test_build_query__adds_the_russian_trailer_suffix():
    assert build_query(Video(title="Heat", year=1995)) == "Heat 1995 трейлер"


def test_build_query__without_year():
    assert build_query(Video(title="Heat", year=None)) == "Heat трейлер"


def test_trailer_filename__is_derived_from_the_row():
    assert trailer_filename(Video(pk=7, title="Heat", year=1995)) == "7-heat-1995.mp4"


def test_trailer_filename__keeps_a_cyrillic_title():
    assert trailer_filename(Video(pk=7, title="Брат", year=1997)) == "7-брат-1997.mp4"


@pytest.mark.django_db
class TestDownloadTrailer:
    def test_download__stores_the_file(self, trailer_settings, monkeypatch):
        video = VideoFactory(title="Heat", year=1995)
        queries = []

        def fake_fetch(query, target):
            queries.append(query)
            write_trailer(query, target)

        monkeypatch.setattr(trailers, "fetch_trailer_file", fake_fetch)

        result = download_trailer(video)

        video.refresh_from_db()
        assert result == FetchStatus.FETCHED
        assert video.trailer == f"{video.pk}-heat-1995.mp4"
        assert video.trailer_attempts == 1
        assert (Path(trailer_settings.CINEMA_TRAILERS_DIR) / video.trailer).is_file()
        assert queries == ["Heat 1995 трейлер"]

    def test_download__never_redownloads_an_existing_file(self, trailer_settings, monkeypatch):
        video = VideoFactory(title="Heat", year=1995)
        target = Path(trailer_settings.CINEMA_TRAILERS_DIR) / trailer_filename(video)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"mp4")

        def fail(query, target):
            raise AssertionError("yt-dlp must not run for an existing trailer")

        monkeypatch.setattr(trailers, "fetch_trailer_file", fail)

        result = download_trailer(video)

        video.refresh_from_db()
        assert result == FetchStatus.FETCHED
        assert video.trailer == target.name

    def test_download__failure_is_retryable(self, trailer_settings, monkeypatch):
        monkeypatch.setattr(trailers, "fetch_trailer_file", raise_download_error)
        video = VideoFactory()

        result = download_trailer(video)

        video.refresh_from_db()
        assert result == FetchStatus.ERROR
        assert video.trailer_attempts == 1
        assert Video.objects.pending_trailers().filter(pk=video.pk).exists()

    def test_download__gives_up_after_max_attempts(self, trailer_settings, monkeypatch):
        monkeypatch.setattr(trailers, "fetch_trailer_file", raise_download_error)
        video = VideoFactory(trailer_attempts=2)

        result = download_trailer(video)

        video.refresh_from_db()
        assert result == FetchStatus.NOT_FOUND
        assert video.trailer_attempts == 3
        assert not Video.objects.pending_trailers().filter(pk=video.pk).exists()

    def test_download__missing_ytdlp_does_not_burn_attempts(self, settings, tmp_path, monkeypatch):
        settings.CINEMA_TRAILERS_DIR = str(tmp_path)
        monkeypatch.setattr(trailers.shutil, "which", lambda binary: None)
        video = VideoFactory()

        result = download_trailer(video)

        video.refresh_from_db()
        assert result == FetchStatus.PENDING
        assert video.trailer_attempts == 0

    def test_download__empty_result_is_a_failure(self, trailer_settings, monkeypatch):
        monkeypatch.setattr(trailers, "fetch_trailer_file", lambda query, target: None)
        video = VideoFactory()

        result = download_trailer(video)

        video.refresh_from_db()
        assert result == FetchStatus.ERROR
        assert video.trailer == ""


@pytest.mark.django_db
class TestProcessPendingTrailers:
    def test_process__downloads_one_batch(self, trailer_settings, monkeypatch):
        monkeypatch.setattr(trailers, "fetch_trailer_file", write_trailer)
        VideoFactory.create_batch(3)

        assert process_pending_trailers(limit=2) == 2
        assert Video.objects.pending_trailers().count() == 1
