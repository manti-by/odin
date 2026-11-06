import os

import pytest

from odin.apps.video.models import FetchStatus, Video
from odin.apps.video.services.scanner import parse_filename, scan_library, sync_video


@pytest.mark.parametrize(
    ("filename", "expected"),
    (
        ("Heat - 1995.mkv", ("Heat", 1995)),
        ("Dune - 2021 - 4K.mkv", ("Dune", 2021)),
        ("Spider-Man - No Way Home - 2021.mkv", ("Spider-Man - No Way Home", 2021)),
        ("Брат - 1997.avi", ("Брат", 1997)),
        ("Heat (1995).mkv", ("Heat", 1995)),
        ("The Matrix (1999) 1080p.mkv", ("The Matrix", 1999)),
        ("no-year.mkv", ("no-year", None)),
    ),
)
def test_parse_filename(filename, expected):
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

    def test_scan__modified_file_keeps_fetched_metadata(self, tmp_path, settings):
        settings.VIDEO_MEDIA_DIRS = (str(tmp_path),)
        path = tmp_path / "Heat - 1995.mkv"
        path.write_bytes(b"video")
        scan_library()
        video = Video.objects.get()
        Video.objects.filter(pk=video.pk).update(metadata_status=FetchStatus.FETCHED, title_omdb="Heat (1995 film)")

        path.write_bytes(b"re-encoded video")
        os.utime(path, (1_700_000_000, 1_700_000_000))
        stats = scan_library()

        video.refresh_from_db()
        assert stats["updated"] == 1
        assert video.title == "Heat"
        assert video.title_omdb == "Heat (1995 film)"
        assert video.metadata_status == FetchStatus.FETCHED
        assert video.size == len(b"re-encoded video")

    def test_scan__parsed_name_change_invalidates_omdb(self, tmp_path, settings):
        settings.VIDEO_MEDIA_DIRS = (str(tmp_path),)
        path = tmp_path / "Брат - 1997.mkv"
        path.write_bytes(b"video")
        scan_library()
        video = Video.objects.get()
        Video.objects.filter(pk=video.pk).update(
            filename="Брат - 1990.mkv",
            metadata_status=FetchStatus.FETCHED,
            title_omdb="Брат (1990 film)",
            imdb_rating="7.0",
            title_en="Brother",
            translation_status=FetchStatus.FETCHED,
            translation_attempts=1,
        )

        path.write_bytes(b"re-encoded video")
        os.utime(path, (1_700_000_000, 1_700_000_000))
        scan_library()

        video.refresh_from_db()
        assert video.title == "Брат"
        assert video.year == 1997
        assert video.title_en == ""
        assert video.translation_status == FetchStatus.PENDING
        assert video.translation_attempts == 0
        assert video.title_omdb == ""
        assert video.imdb_rating is None
        assert video.metadata_status == FetchStatus.PENDING
        assert video.metadata_attempts == 0

    def test_scan__latin_title_skips_translation(self, tmp_path, settings):
        settings.VIDEO_MEDIA_DIRS = (str(tmp_path),)
        (tmp_path / "Heat - 1995.mkv").write_bytes(b"video")

        scan_library()

        video = Video.objects.get()
        assert video.title_en == "Heat"
        assert video.translation_status == FetchStatus.FETCHED

    def test_scan__modified_file_keeps_translation(self, tmp_path, settings):
        settings.VIDEO_MEDIA_DIRS = (str(tmp_path),)
        path = tmp_path / "Брат - 1997.mkv"
        path.write_bytes(b"video")
        scan_library()
        Video.objects.update(
            title_en="Brother",
            translation_status=FetchStatus.FETCHED,
            translation_attempts=2,
        )

        path.write_bytes(b"re-encoded video")
        os.utime(path, (1_700_000_000, 1_700_000_000))
        scan_library()

        video = Video.objects.get()
        assert video.title_en == "Brother"
        assert video.translation_status == FetchStatus.FETCHED
        assert video.translation_attempts == 2

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
