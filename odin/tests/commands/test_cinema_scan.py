import pytest

from django.core.management import call_command

import odin.apps.cinema.management.commands.cinema_scan as cinema_scan
from odin.apps.cinema.models import Video


@pytest.mark.django_db
class TestCinemaScanCommand:
    def test_scan__creates_rows_without_fetch_phases(self, tmp_path, settings):
        settings.CINEMA_MEDIA_DIRS = (str(tmp_path),)
        (tmp_path / "Heat (1995).mkv").write_bytes(b"video")
        (tmp_path / "Брат (1997).avi").write_bytes(b"video")

        call_command("cinema_scan", "--no-metadata", "--no-trailers")

        assert Video.objects.count() == 2
        assert Video.objects.get(title="Брат").year == 1997

    def test_scan__runs_both_fetch_phases(self, tmp_path, settings, monkeypatch):
        settings.CINEMA_MEDIA_DIRS = (str(tmp_path),)
        settings.CINEMA_SCAN_BATCH_SIZE = 4
        (tmp_path / "Heat (1995).mkv").write_bytes(b"video")
        calls = []

        def phase(name):
            return lambda limit: calls.append((name, limit))

        monkeypatch.setattr(cinema_scan, "process_pending_metadata", phase("metadata"))
        monkeypatch.setattr(cinema_scan, "process_pending_trailers", phase("trailers"))

        call_command("cinema_scan")

        assert calls == [("metadata", 4), ("trailers", 4)]

    def test_scan__skips_phases_on_flags(self, tmp_path, settings, monkeypatch):
        settings.CINEMA_MEDIA_DIRS = (str(tmp_path),)
        calls = []

        monkeypatch.setattr(cinema_scan, "process_pending_metadata", lambda limit: calls.append("metadata"))
        monkeypatch.setattr(cinema_scan, "process_pending_trailers", lambda limit: calls.append("trailers"))

        call_command("cinema_scan", "--no-metadata")

        assert calls == ["trailers"]

    def test_scan__respects_the_limit_option(self, tmp_path, settings, monkeypatch):
        settings.CINEMA_MEDIA_DIRS = (str(tmp_path),)
        (tmp_path / "Heat (1995).mkv").write_bytes(b"video")
        limits = []

        monkeypatch.setattr(cinema_scan, "process_pending_metadata", lambda limit: limits.append(limit))
        monkeypatch.setattr(cinema_scan, "process_pending_trailers", lambda limit: limits.append(limit))

        call_command("cinema_scan", "--limit", "2")

        assert limits == [2, 2]
