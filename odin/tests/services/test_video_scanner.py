import os

import pytest

from odin.apps.video.models import FetchStatus, Video
from odin.apps.video.services.scanner import parse_filename, scan_library, sync_video


@pytest.mark.parametrize(
    ("filename", "expected"),
    (
        ("Heat - 1995.mkv", ("Heat", 1995, False)),
        ("Movie.Name.2010.1080p - 2010.mp4", ("Movie.Name.2010.1080p", 2010, False)),
        ("The Matrix - 1999.mkv", ("The Matrix", 1999, False)),
        ("Брат - 1997.avi", ("Брат", 1997, False)),
        ("no-year.mkv", ("no-year", None, False)),
    ),
)
def test_parse_filename(filename, expected):
    assert parse_filename(filename) == expected


@pytest.mark.parametrize(
    ("filename", "expected"),
    (
        ("Дюна - 2021 - 4K.mkv", ("Дюна", 2021, True)),
        ("Майкл - 2026 - 4К.mkv", ("Майкл", 2026, True)),  # noqa: RUF001
        ("Обсессия - 2025 - 4К.mkv", ("Обсессия", 2025, True)),  # noqa: RUF001
        ("2001 год Космическая одиссея - 1968 - 4K.mkv", ("2001 год Космическая одиссея", 1968, True)),
        ("Дюна. Часть вторая - 2024.mkv", ("Дюна. Часть вторая", 2024, False)),
        ("Кловерфилд, 10 - 2016.mkv", ("Кловерфилд, 10", 2016, False)),
    ),
)
def test_parse_filename__real_library_names(filename, expected):
    assert parse_filename(filename) == expected


@pytest.mark.django_db
class TestScanLibrary:
    def test_scan__creates_video_rows(self, tmp_path, settings):
        settings.VIDEO_MEDIA_DIRS = (str(tmp_path),)
        (tmp_path / "Heat - 1995.mkv").write_bytes(b"video")
        (tmp_path / "notes.txt").write_bytes(b"skip")
        (tmp_path / ".hidden").mkdir()
        (tmp_path / ".hidden" / "Secret - 2020.mkv").write_bytes(b"skip")

        stats = scan_library()

        assert stats["created"] == 1
        video = Video.objects.get()
        assert video.title == "Heat"
        assert video.year == 1995
        assert video.filename == "Heat - 1995.mkv"
        assert video.path == str((tmp_path / "Heat - 1995.mkv").resolve())
        assert video.is_available is True

    def test_scan__marks_4k_files(self, tmp_path, settings):
        settings.VIDEO_MEDIA_DIRS = (str(tmp_path),)
        (tmp_path / "Дюна - 2021 - 4K.mkv").write_bytes(b"video")
        (tmp_path / "Дюна. Часть вторая - 2024.mkv").write_bytes(b"video")

        scan_library()

        assert Video.objects.get(title="Дюна").is_4k is True
        assert Video.objects.get(title="Дюна. Часть вторая").is_4k is False

    def test_scan__unchanged_file_is_not_rewritten(self, tmp_path, settings):
        settings.VIDEO_MEDIA_DIRS = (str(tmp_path),)
        path = tmp_path / "Heat - 1995.mkv"
        path.write_bytes(b"video")
        scan_library()
        video = Video.objects.get()
        Video.objects.filter(pk=video.pk).update(title="HEAT (edited)")  # metadata already applied

        stats = scan_library()

        video.refresh_from_db()
        assert stats["updated"] == 0
        assert video.title == "HEAT (edited)"

    def test_scan__modified_file_keeps_fetched_metadata_title(self, tmp_path, settings):
        settings.VIDEO_MEDIA_DIRS = (str(tmp_path),)
        path = tmp_path / "Heat - 1995.mkv"
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
        settings.VIDEO_MEDIA_DIRS = (str(tmp_path),)
        path = tmp_path / "Heat - 1995.mkv"
        kept = tmp_path / "Brat - 1997.mkv"
        path.write_bytes(b"video")
        kept.write_bytes(b"video")
        scan_library()
        path.unlink()

        stats = scan_library()

        assert stats["missing"] == 1
        assert Video.objects.get(title="Heat").is_available is False
        assert Video.objects.get(title="Brat").is_available is True

    def test_scan__empty_root_keeps_rows_available(self, tmp_path, settings):
        settings.VIDEO_MEDIA_DIRS = (str(tmp_path),)
        path = tmp_path / "Heat - 1995.mkv"
        path.write_bytes(b"video")
        scan_library()
        path.unlink()

        stats = scan_library()

        assert stats["missing"] == 0
        assert Video.objects.get().is_available is True

    def test_scan__restores_a_returning_file(self, tmp_path, settings):
        settings.VIDEO_MEDIA_DIRS = (str(tmp_path),)
        path = tmp_path / "Heat - 1995.mkv"
        _other = tmp_path / "Brat - 1997.mkv"
        path.write_bytes(b"video")
        _other.write_bytes(b"video")
        scan_library()
        path.unlink()
        scan_library()
        path.write_bytes(b"video")

        scan_library()

        assert Video.objects.get(title="Heat").is_available is True

    def test_scan__missing_root_keeps_rows(self, tmp_path, settings):
        settings.VIDEO_MEDIA_DIRS = (str(tmp_path),)
        (tmp_path / "Heat - 1995.mkv").write_bytes(b"video")
        scan_library()

        settings.VIDEO_MEDIA_DIRS = (str(tmp_path / "unmounted"),)
        stats = scan_library()

        assert stats["missing"] == 0
        assert Video.objects.get().is_available is True

    def test_scan__unparsable_name_is_kept(self, tmp_path, settings):
        settings.VIDEO_MEDIA_DIRS = (str(tmp_path),)
        (tmp_path / "home-video.mkv").write_bytes(b"video")

        scan_library()

        video = Video.objects.get()
        assert video.title == "home-video"
        assert video.year is None

    def test_scan__symlink_outside_media_dirs_is_skipped(self, tmp_path, settings):
        media_dir = tmp_path / "media"
        media_dir.mkdir()
        outside = tmp_path / "secret.mkv"
        outside.write_bytes(b"secret")
        (media_dir / "Secret - 2020.mkv").symlink_to(outside)
        settings.VIDEO_MEDIA_DIRS = (str(media_dir),)

        stats = scan_library()

        assert stats["found"] == 0
        assert not Video.objects.exists()

    def test_sync_video__creates_row(self, tmp_path, settings):
        settings.VIDEO_MEDIA_DIRS = (str(tmp_path),)
        path = tmp_path / "Heat - 1995.mkv"
        path.write_bytes(b"video")

        result = sync_video(path)

        assert result is not None
        video, created, changed = result
        assert (created, changed) == (True, True)
        assert video.pk is not None
        assert video.title == "Heat"

    def test_sync_video__rejects_a_path_outside_media_dirs(self, tmp_path, settings):
        media_dir = tmp_path / "media"
        media_dir.mkdir()
        settings.VIDEO_MEDIA_DIRS = (str(media_dir),)
        path = tmp_path / "Heat - 1995.mkv"
        path.write_bytes(b"video")

        assert sync_video(path) is None
