from pathlib import Path
from unittest.mock import Mock

import pytest

from odin.apps.video.models import FetchStatus, Video
from odin.apps.video.services import trailers
from odin.apps.video.services.trailers import (
    TrailerDownloadError,
    build_query,
    download_trailer,
    fetch_trailer_file,
    process_pending_trailers,
    trailer_filename,
)
from odin.tests.factories import VideoFactory


@pytest.fixture
def trailer_settings(tmp_path, settings, monkeypatch):
    settings.VIDEO_TRAILERS_DIR = str(tmp_path)
    settings.VIDEO_FETCH_MAX_ATTEMPTS = 3
    settings.VIDEO_SCAN_BATCH_SIZE = 5
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


class TestFetchTrailerFile:
    def test_fetch_file__moves_the_downloaded_mp4_into_place(self, tmp_path, monkeypatch):
        target = tmp_path / "1-heat-1995.mp4"
        commands = []

        def fake_run(command, **kwargs):
            commands.append(command)
            scratch = Path(command[command.index("--paths") + 1])
            (scratch / "dQw4w9WgXcQ.mp4").write_bytes(b"mp4")
            return Mock(returncode=0, stderr="")

        monkeypatch.setattr(trailers.subprocess, "run", fake_run)

        fetch_trailer_file("Heat 1995 трейлер", target)

        assert target.read_bytes() == b"mp4"
        assert "--ignore-config" in commands[0]
        assert "best[ext=mp4]/bestvideo[ext=mp4]+bestaudio[ext=m4a]" in commands[0]

    def test_fetch_file__rejects_a_non_mp4_download(self, tmp_path, monkeypatch):
        target = tmp_path / "1-heat-1995.mp4"

        def fake_run(command, **kwargs):
            scratch = Path(command[command.index("--paths") + 1])
            (scratch / "dQw4w9WgXcQ.webm").write_bytes(b"webm")
            return Mock(returncode=0, stderr="")

        monkeypatch.setattr(trailers.subprocess, "run", fake_run)

        with pytest.raises(TrailerDownloadError):
            fetch_trailer_file("Heat 1995 трейлер", target)

        assert not target.exists()

    def test_fetch_file__does_not_pick_a_sidecar(self, tmp_path, monkeypatch):
        target = tmp_path / "1-heat-1995.mp4"

        def fake_run(command, **kwargs):
            scratch = Path(command[command.index("--paths") + 1])
            (scratch / "dQw4w9WgXcQ.info.json").write_text("{}")
            (scratch / "dQw4w9WgXcQ.mp4").write_bytes(b"mp4")
            return Mock(returncode=0, stderr="")

        monkeypatch.setattr(trailers.subprocess, "run", fake_run)

        fetch_trailer_file("Heat 1995 трейлер", target)

        assert target.read_bytes() == b"mp4"

    def test_fetch_file__fails_when_ytdlp_writes_nothing(self, tmp_path, monkeypatch):
        target = tmp_path / "1-heat-1995.mp4"
        monkeypatch.setattr(trailers.subprocess, "run", Mock(return_value=Mock(returncode=0, stderr="")))

        with pytest.raises(TrailerDownloadError):
            fetch_trailer_file("Heat 1995 трейлер", target)


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
        assert (Path(trailer_settings.VIDEO_TRAILERS_DIR) / video.trailer).is_file()
        assert queries == ["Heat 1995 трейлер"]

    def test_download__never_redownloads_an_existing_file(self, trailer_settings, monkeypatch):
        video = VideoFactory(title="Heat", year=1995)
        target = Path(trailer_settings.VIDEO_TRAILERS_DIR) / trailer_filename(video)
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
        settings.VIDEO_TRAILERS_DIR = str(tmp_path)
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
