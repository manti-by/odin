from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from django.utils import timezone
from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APIClient

from odin.apps.boiler.services.ebusd import EbusdError
from odin.apps.boiler.services.mode import BoilerMode
from odin.apps.boiler.services.schedule import BOIL_HOUR, CLEAR_HOUR, get_next_boil_schedule


MINSK = ZoneInfo("Europe/Minsk")


@pytest.fixture
def boiler_state(settings, tmp_path):
    settings.BOILER_STATE_FILE = str(tmp_path / "state")
    settings.BOILER_LOCK_FILE = str(tmp_path / "state.lock")
    return tmp_path / "state"


@pytest.fixture(autouse=True)
def ebusd_online(monkeypatch):
    monkeypatch.setattr("odin.apps.boiler.services.ebusd.EbusdClient.command", lambda self, command: "info")


@pytest.mark.django_db
class TestBoilerStatusAPI:
    def setup_method(self):
        self.client = APIClient()
        self.url = reverse("api:v1:boiler:status")

    def test_status__panel_mode(self, boiler_state):
        response = self.client.get(self.url, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["mode"] == BoilerMode.MIXED
        assert response.data["override_active"] is False
        assert response.data["target_temp"] is None
        assert response.data["hwc_temp"] is None
        assert response.data["override_updated_at"] is None
        assert response.data["ebusd_alive"] is True

    def test_status__boiling_override(self, boiler_state):
        boiler_state.write_text("water;0;55;-;0;0;0;0;0;0\n")

        response = self.client.get(self.url, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["mode"] == BoilerMode.BOILING
        assert response.data["override_active"] is True
        assert response.data["target_temp"] == 0
        assert response.data["hwc_temp"] == 55
        assert response.data["override_updated_at"] is not None

    def test_status__ebusd_offline(self, monkeypatch, boiler_state):
        def fail(self, command):
            raise EbusdError("offline")

        monkeypatch.setattr("odin.apps.boiler.services.ebusd.EbusdClient.command", fail)

        response = self.client.get(self.url, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["ebusd_alive"] is False

    def test_status__next_boil_schedule(self, boiler_state):
        response = self.client.get(self.url, format="json")
        boil = datetime.fromisoformat(response.data["next_boil_at"])
        clear = datetime.fromisoformat(response.data["next_clear_at"])

        assert boil > timezone.now()
        assert boil.weekday() == 5  # Saturday
        assert boil.hour == BOIL_HOUR
        assert clear - boil == timedelta(hours=CLEAR_HOUR - BOIL_HOUR)


class TestGetNextBoilSchedule:
    def test__before_boil__both_today(self, monkeypatch):
        monkeypatch.setattr(timezone, "localtime", lambda *args, **kwargs: datetime(2026, 9, 19, 0, 30, tzinfo=MINSK))

        boil, clear = get_next_boil_schedule()

        assert boil == datetime(2026, 9, 19, BOIL_HOUR, 0, tzinfo=MINSK)
        assert clear == datetime(2026, 9, 19, CLEAR_HOUR, 0, tzinfo=MINSK)

    def test__inside_boil_window__clear_today_boil_next_week(self, monkeypatch):
        monkeypatch.setattr(timezone, "localtime", lambda *args, **kwargs: datetime(2026, 9, 19, 1, 30, tzinfo=MINSK))

        boil, clear = get_next_boil_schedule()

        assert boil == datetime(2026, 9, 26, BOIL_HOUR, 0, tzinfo=MINSK)
        assert clear == datetime(2026, 9, 19, CLEAR_HOUR, 0, tzinfo=MINSK)

    def test__after_clear__both_next_week(self, monkeypatch):
        monkeypatch.setattr(timezone, "localtime", lambda *args, **kwargs: datetime(2026, 9, 19, 2, 30, tzinfo=MINSK))

        boil, clear = get_next_boil_schedule()

        assert boil == datetime(2026, 9, 26, BOIL_HOUR, 0, tzinfo=MINSK)
        assert clear == datetime(2026, 9, 26, CLEAR_HOUR, 0, tzinfo=MINSK)
