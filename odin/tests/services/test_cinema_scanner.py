import os

import pytest

from odin.apps.cinema.models import FetchStatus, Video
from odin.apps.cinema.services.scanner import parse_filename, scan_library, sync_video


@pytest.mark.parametrize(
    ("filename", "expected"),
    (
        ("Heat (1995).mkv", ("Heat", 1995)),
        ("Movie.Name.2010.1080p (2010).mp4", ("Movie.Name.2010.1080p", 2010)),
        ("The Matrix (1999) 1080p.mkv", ("The Matrix", 1999)),
        ("Брат (1997).avi", ("Брат", 1997)),
        ("no-year.mkv", ("no-year", None)),
    ),
)
def test_parse_filename(filename, expected):
    assert parse_filename(filename) == expected


@pytest.mark.django_db
class TestScanLibrary:
    def test_scan__creates_video_rows(self, tmp_path, settings):
        settings.CINEMA_MEDIA_DIRS = (str(tmp_path),)
        (tmp_path / "Heat (1995).mkv").write_bytes(b"video")
        (tmp_path / "notes.txt").write_bytes(b"skip")
        (tmp_path / ".hidden").mkdir()
        (tmp_path / ".hidden" / "Secret (2020).mkv").write_bytes(b"skip")

        stats = scan_library()

        assert stats["created"] == 1
        video = Video.objects.get()
        assert video.title == "Heat"
        assert video.year == 1995
        assert video.filename == "Heat (1995).mkv"
        assert video.path == str((tmp_path / "Heat (1995).mkv").resolve())
        assert video.is_available is True

    def test_scan__unchanged_file_is_not_rewritten(self, tmp_path, settings):
        settings.CINEMA_MEDIA_DIRS = (str(tmp_path),)
        path = tmp_path / "Heat (1995).mkv"
        path.write_bytes(b"video")
        scan_library()
        video = Video.objects.get()
        Video.objects.filter(pk=video.pk).update(title="HEAT (edited)")  # metadata already applied

        stats = scan_library()

        video.refresh_from_db()
        assert stats["updated"] == 0
        assert video.title == "HEAT (edited)"

    def test_scan__modified_file_keeps_fetched_metadata_title(self, tmp_path, settings):
        settings.CINEMA_MEDIA_DIRS = (str(tmp_path),)
        path = tmp_path / "Heat (1995).mkv"
        path.write_bytes(b"video")
        scan_library()
        video = Video.objects.get()
        Video.objects.filter(pk=video.pk).update(metadata_status=FetchStatus.FETCHED, title="Heat (1995 film)")

        path.write_bytes(b"re-encoded video")
        os.utime(path, (1_700_000_000, 1_700_000_000))
        stats = scan_library()

        video.refresh_from_db()
        assert stats["updated"] == 1
        assert video.title == "Heat (1995 film)"
        assert video.size == len(b"re-encoded video")

    def test_scan__marks_removed_files_unavailable(self, tmp_path, settings):
        settings.CINEMA_MEDIA_DIRS = (str(tmp_path),)
        path = tmp_path / "Heat (1995).mkv"
        path.write_bytes(b"video")
        scan_library()
        path.unlink()

        stats = scan_library()

        assert stats["missing"] == 1
        assert Video.objects.get().is_available is False

    def test_scan__restores_a_returning_file(self, tmp_path, settings):
        settings.CINEMA_MEDIA_DIRS = (str(tmp_path),)
        path = tmp_path / "Heat (1995).mkv"
        path.write_bytes(b"video")
        scan_library()
        path.unlink()
        scan_library()
        path.write_bytes(b"video")

        scan_library()

        assert Video.objects.get().is_available is True

    def test_scan__missing_root_keeps_rows(self, tmp_path, settings):
        settings.CINEMA_MEDIA_DIRS = (str(tmp_path),)
        (tmp_path / "Heat (1995).mkv").write_bytes(b"video")
        scan_library()

        settings.CINEMA_MEDIA_DIRS = (str(tmp_path / "unmounted"),)
        stats = scan_library()

        assert stats["missing"] == 0
        assert Video.objects.get().is_available is True

    def test_scan__unparsable_name_is_kept(self, tmp_path, settings):
        settings.CINEMA_MEDIA_DIRS = (str(tmp_path),)
        (tmp_path / "home-video.mkv").write_bytes(b"video")

        scan_library()

        video = Video.objects.get()
        assert video.title == "home-video"
        assert video.year is None

    def test_sync_video__creates_row(self, tmp_path):
        path = tmp_path / "Heat (1995).mkv"
        path.write_bytes(b"video")

        video, created, changed = sync_video(path)

        assert (created, changed) == (True, True)
        assert video.pk is not None
        assert video.title == "Heat"
