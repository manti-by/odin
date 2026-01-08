from datetime import UTC, datetime
from datetime import timezone as dt_timezone
from unittest.mock import patch

import pytest

from rest_framework.test import APIClient

from odin.apps.relays.models import Relay, RelayState
from odin.tests.factories import RelayFactory


@pytest.mark.django_db
class TestRelaysModel:
    def setup_method(self):
        self.client = APIClient()
        self.relay: Relay = RelayFactory()  # noqa

    def test_relays__state_property(self):
        """Test that relay state property works correctly."""
        assert self.relay.state == "UNKNOWN"

        self.relay.context = {"state": "ON"}
        assert self.relay.state == "ON"

        self.relay.context["state"] = "OFF"
        self.relay.save()
        self.relay.refresh_from_db()
        assert self.relay.state == "OFF"

    def test_relays__target_state_returns_on_when_schedule_is_true(self):
        """Test that target_state returns ON when schedule says true."""
        self.relay.context = {"schedule": {"1": {"10": True}}}
        self.relay.save()

        local_time = datetime(2025, 1, 6, 10, 30, 0, tzinfo=dt_timezone(UTC.utcoffset(datetime.now(UTC))))
        with patch("odin.apps.relays.models.timezone.localtime", return_value=local_time):
            assert self.relay.target_state == RelayState.ON

    def test_relays__target_state_returns_off_when_schedule_is_false(self):
        """Test that target_state returns OFF when schedule says false."""
        self.relay.context = {"schedule": {"1": {"11": False}}}
        self.relay.save()

        local_time = datetime(2025, 1, 6, 11, 30, 0, tzinfo=dt_timezone(UTC.utcoffset(datetime.now(UTC))))
        with patch("odin.apps.relays.models.timezone.localtime", return_value=local_time):
            assert self.relay.target_state == RelayState.OFF

    def test_relays__target_state_returns_unknown_when_no_schedule(self):
        """Test that target_state returns UNKNOWN when no schedule in context."""
        self.relay.context = {}
        self.relay.save()

        local_time = datetime(2025, 1, 6, 10, 30, 0, tzinfo=dt_timezone(UTC.utcoffset(datetime.now(UTC))))
        with patch("odin.apps.relays.models.timezone.localtime", return_value=local_time):
            assert self.relay.target_state == RelayState.UNKNOWN

    def test_relays__target_state_returns_unknown_when_no_day_schedule(self):
        """Test that target_state returns UNKNOWN when no schedule for current day."""
        self.relay.context = {"schedule": {"2": {"10": True}}}
        self.relay.save()

        local_time = datetime(2025, 1, 6, 10, 30, 0, tzinfo=dt_timezone(UTC.utcoffset(datetime.now(UTC))))
        with patch("odin.apps.relays.models.timezone.localtime", return_value=local_time):
            assert self.relay.target_state == RelayState.UNKNOWN

    def test_relays__target_state_returns_unknown_when_no_hour_schedule(self):
        """Test that target_state returns UNKNOWN when no schedule for current hour."""
        self.relay.context = {"schedule": {"1": {"10": True}}}
        self.relay.save()

        local_time = datetime(2025, 1, 6, 15, 30, 0, tzinfo=dt_timezone(UTC.utcoffset(datetime.now(UTC))))
        with patch("odin.apps.relays.models.timezone.localtime", return_value=local_time):
            assert self.relay.target_state == RelayState.UNKNOWN

    def test_relays__target_state_uses_schedule_from_context(self):
        """Test target_state uses schedule dict from context like schedule.json format."""
        schedule = {
            "schedule": {
                "0": {"10": True, "11": False, "12": True},
                "1": {"08": False, "09": True},
                "2": {},
                "3": {"18": True},
            }
        }
        self.relay.context = schedule
        self.relay.save()

        local_time = datetime(2025, 1, 5, 10, 30, 0, tzinfo=dt_timezone(UTC.utcoffset(datetime.now(UTC))))
        with patch("odin.apps.relays.models.timezone.localtime", return_value=local_time):
            assert self.relay.target_state == RelayState.ON

        local_time = datetime(2025, 1, 5, 11, 30, 0, tzinfo=dt_timezone(UTC.utcoffset(datetime.now(UTC))))
        with patch("odin.apps.relays.models.timezone.localtime", return_value=local_time):
            assert self.relay.target_state == RelayState.OFF

        local_time = datetime(2025, 1, 6, 9, 30, 0, tzinfo=dt_timezone(UTC.utcoffset(datetime.now(UTC))))
        with patch("odin.apps.relays.models.timezone.localtime", return_value=local_time):
            assert self.relay.target_state == RelayState.ON

        local_time = datetime(2025, 1, 6, 8, 30, 0, tzinfo=dt_timezone(UTC.utcoffset(datetime.now(UTC))))
        with patch("odin.apps.relays.models.timezone.localtime", return_value=local_time):
            assert self.relay.target_state == RelayState.OFF

        local_time = datetime(2025, 1, 7, 12, 30, 0, tzinfo=dt_timezone(UTC.utcoffset(datetime.now(UTC))))
        with patch("odin.apps.relays.models.timezone.localtime", return_value=local_time):
            assert self.relay.target_state == RelayState.UNKNOWN

        local_time = datetime(2025, 1, 8, 18, 30, 0, tzinfo=dt_timezone(UTC.utcoffset(datetime.now(UTC))))
        with patch("odin.apps.relays.models.timezone.localtime", return_value=local_time):
            assert self.relay.target_state == RelayState.ON
