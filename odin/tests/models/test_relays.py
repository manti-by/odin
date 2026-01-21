from datetime import UTC, datetime
from datetime import timezone as dt_timezone
from decimal import Decimal
from unittest.mock import patch

import pytest

from rest_framework.test import APIClient

from odin.apps.relays.models import Relay, RelayState, RelayType
from odin.apps.sensors.models import Sensor
from odin.tests.factories import RelayFactory, SensorFactory, SensorLogFactory


@pytest.mark.django_db
class TestRelaysModel:
    def setup_method(self):
        self.client = APIClient()
        self.relay: Relay = RelayFactory(type=RelayType.PUMP)  # noqa

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
        with patch("odin.apps.relays.services.timezone.localtime", return_value=local_time):
            assert self.relay.target_state == RelayState.ON

    def test_relays__target_state_returns_off_when_schedule_is_false(self):
        """Test that target_state returns OFF when schedule says false."""
        self.relay.context = {"schedule": {"1": {"11": False}}}
        self.relay.save()

        local_time = datetime(2025, 1, 6, 11, 30, 0, tzinfo=dt_timezone(UTC.utcoffset(datetime.now(UTC))))
        with patch("odin.apps.relays.services.timezone.localtime", return_value=local_time):
            assert self.relay.target_state == RelayState.OFF

    def test_relays__target_state_returns_unknown_when_no_schedule(self):
        """Test that target_state returns UNKNOWN when no schedule in context."""
        self.relay.context = {}
        self.relay.save()

        local_time = datetime(2025, 1, 6, 10, 30, 0, tzinfo=dt_timezone(UTC.utcoffset(datetime.now(UTC))))
        with patch("odin.apps.relays.services.timezone.localtime", return_value=local_time):
            assert self.relay.target_state == RelayState.UNKNOWN

    def test_relays__target_state_returns_unknown_when_no_day_schedule(self):
        """Test that target_state returns UNKNOWN when no schedule for current day."""
        self.relay.context = {"schedule": {"2": {"10": True}}}
        self.relay.save()

        local_time = datetime(2025, 1, 6, 10, 30, 0, tzinfo=dt_timezone(UTC.utcoffset(datetime.now(UTC))))
        with patch("odin.apps.relays.services.timezone.localtime", return_value=local_time):
            assert self.relay.target_state == RelayState.UNKNOWN

    def test_relays__target_state_returns_unknown_when_no_hour_schedule(self):
        """Test that target_state returns UNKNOWN when no schedule for current hour."""
        self.relay.context = {"schedule": {"1": {"10": True}}}
        self.relay.save()

        local_time = datetime(2025, 1, 6, 15, 30, 0, tzinfo=dt_timezone(UTC.utcoffset(datetime.now(UTC))))
        with patch("odin.apps.relays.services.timezone.localtime", return_value=local_time):
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
        with patch("odin.apps.relays.services.timezone.localtime", return_value=local_time):
            assert self.relay.target_state == RelayState.ON

        local_time = datetime(2025, 1, 5, 11, 30, 0, tzinfo=dt_timezone(UTC.utcoffset(datetime.now(UTC))))
        with patch("odin.apps.relays.services.timezone.localtime", return_value=local_time):
            assert self.relay.target_state == RelayState.OFF

        local_time = datetime(2025, 1, 6, 9, 30, 0, tzinfo=dt_timezone(UTC.utcoffset(datetime.now(UTC))))
        with patch("odin.apps.relays.services.timezone.localtime", return_value=local_time):
            assert self.relay.target_state == RelayState.ON

        local_time = datetime(2025, 1, 6, 8, 30, 0, tzinfo=dt_timezone(UTC.utcoffset(datetime.now(UTC))))
        with patch("odin.apps.relays.services.timezone.localtime", return_value=local_time):
            assert self.relay.target_state == RelayState.OFF

        local_time = datetime(2025, 1, 7, 12, 30, 0, tzinfo=dt_timezone(UTC.utcoffset(datetime.now(UTC))))
        with patch("odin.apps.relays.services.timezone.localtime", return_value=local_time):
            assert self.relay.target_state == RelayState.UNKNOWN

        local_time = datetime(2025, 1, 8, 18, 30, 0, tzinfo=dt_timezone(UTC.utcoffset(datetime.now(UTC))))
        with patch("odin.apps.relays.services.timezone.localtime", return_value=local_time):
            assert self.relay.target_state == RelayState.ON


@pytest.mark.django_db
class TestRelaysSensorProperty:
    def setup_method(self):
        self.relay: Relay = RelayFactory()  # noqa

    def test_relays__sensor_returns_none_when_no_linked_sensor(self):
        """Test that sensor property returns None when relay_id doesn't match any sensor."""
        self.relay.relay_id = "nonexistent"
        self.relay.save()
        assert self.relay.sensor is None

    def test_relays__sensor_returns_linked_sensor(self):
        """Test that sensor property returns the linked sensor."""
        sensor = SensorFactory(relay_id=self.relay.relay_id)
        assert self.relay.sensor == sensor

    def test_relays__sensor_returns_most_recent_when_multiple(self):
        """Test that sensor property returns the most recent sensor."""
        SensorFactory(relay_id=self.relay.relay_id)
        new_sensor = SensorFactory(relay_id=self.relay.relay_id)
        assert self.relay.sensor == new_sensor


@pytest.mark.django_db
class TestRelaysServoTargetState:
    def setup_method(self):
        self.relay: Relay = RelayFactory(type=RelayType.SERVO)  # noqa
        self.sensor: Sensor = SensorFactory(relay_id=self.relay.relay_id)  # noqa

    def test_relays__servo_target_state_returns_unknown_when_no_sensor(self):
        """Test that target_state returns UNKNOWN when no linked sensor."""
        self.relay.relay_id = "nonexistent"
        self.relay.save()
        assert self.relay.target_state == RelayState.UNKNOWN

    def test_relays__servo_target_state_returns_on_when_temp_below_min(self):
        """Test that servo turns ON when temp is below target - hysteresis."""
        self.sensor.context = {"target_temp": "25.0", "hysteresis": "1.0"}
        self.sensor.save()
        SensorLogFactory(sensor_id=self.sensor.sensor_id, temp=Decimal("23.0"))

        assert self.relay.target_state == RelayState.ON

    def test_relays__servo_target_state_returns_on_when_temp_above_max(self):
        """Test that servo turns ON when temp is above target plus hysteresis."""
        self.sensor.context = {"target_temp": "25.0", "hysteresis": "1.0"}
        self.sensor.save()
        SensorLogFactory(sensor_id=self.sensor.sensor_id, temp=Decimal("27.0"))

        assert self.relay.target_state == RelayState.OFF

    def test_relays__servo_target_state_returns_off_when_temp_below_min(self):
        """Test that servo turns OFF when temp is below target - hysteresis."""
        self.sensor.context = {"target_temp": "25.0", "hysteresis": "1.0"}
        self.sensor.save()
        SensorLogFactory(sensor_id=self.sensor.sensor_id, temp=Decimal("23.0"))

        assert self.relay.target_state == RelayState.ON

    def test_relays__servo_target_state_returns_the_same_when_temp_in_range(self):
        """Test that servo turns OFF when temp is within hysteresis range."""
        self.sensor.context = {"target_temp": "25.0", "hysteresis": "1.0"}
        self.sensor.save()
        SensorLogFactory(sensor_id=self.sensor.sensor_id, temp=Decimal("25.0"))

        self.relay.context["state"] = RelayState.OFF
        assert self.relay.target_state == RelayState.OFF

        self.relay.context["state"] = RelayState.ON
        assert self.relay.target_state == RelayState.ON

    def test_relays__servo_target_state_returns_unknown_when_no_temp(self):
        """Test that target_state returns UNKNOWN when sensor has no temperature reading."""
        self.sensor.context = {"target_temp": "25.0", "hysteresis": "1.0"}
        self.sensor.save()

        assert self.relay.target_state == RelayState.UNKNOWN


@pytest.mark.django_db
class TestRelaysTargetStateDispatch:
    def setup_method(self):
        pass

    def test_relays__target_state_returns_pump_state_for_pump_type(self):
        """Test that target_state uses pump_target_state for a PUMP type."""
        relay: Relay = RelayFactory(type=RelayType.PUMP)  # noqa
        relay.context = {"schedule": {"1": {"10": True}}}
        relay.save()

        local_time = datetime(2025, 1, 6, 10, 30, 0, tzinfo=dt_timezone(UTC.utcoffset(datetime.now(UTC))))
        with patch("odin.apps.relays.services.timezone.localtime", return_value=local_time):
            assert relay.target_state == RelayState.ON

    def test_relays__target_state_returns_servo_state_for_servo_type(self):
        """Test that target_state uses target_state for SERVO type."""
        relay: Relay = RelayFactory(type=RelayType.SERVO)  # noqa
        sensor: Sensor = SensorFactory(relay_id=relay.relay_id)  # noqa
        sensor.context = {"target_temp": "25.0", "hysteresis": "1.0"}
        sensor.save()
        SensorLogFactory(sensor_id=sensor.sensor_id, temp=Decimal("23.0"))

        assert relay.target_state == RelayState.ON

    def test_relays__target_state_returns_unknown_for_unknown_type(self):
        """Test that target_state returns UNKNOWN for unknown relay types."""
        relay: Relay = RelayFactory(type=RelayType.VALVE)  # noqa
        assert relay.target_state == RelayState.UNKNOWN


@pytest.mark.django_db
class TestRelaysForceState:
    def setup_method(self):
        self.relay: Relay = RelayFactory(type=RelayType.PUMP)  # noqa

    def test_relays__target_state_returns_force_state_when_set_to_on(self):
        """Test that target_state returns force_state when set to ON."""
        self.relay.force_state = RelayState.ON
        self.relay.save()
        assert self.relay.target_state == RelayState.ON

    def test_relays__target_state_returns_force_state_when_set_to_off(self):
        """Test that target_state returns force_state when set to OFF."""
        self.relay.force_state = RelayState.OFF
        self.relay.save()
        assert self.relay.target_state == RelayState.OFF

    def test_relays__target_state_ignores_schedule_when_force_state_set(self):
        """Test that target_state ignores schedule when force_state is set."""
        self.relay.force_state = RelayState.ON
        self.relay.context = {"schedule": {"1": {"10": False}}}
        self.relay.save()

        local_time = datetime(2025, 1, 6, 10, 30, 0, tzinfo=dt_timezone(UTC.utcoffset(datetime.now(UTC))))
        with patch("odin.apps.relays.services.timezone.localtime", return_value=local_time):
            assert self.relay.target_state == RelayState.ON

    def test_relays__target_state_returns_schedule_when_force_state_is_null(self):
        """Test that target_state uses schedule when force_state is null."""
        self.relay.force_state = None
        self.relay.context = {"schedule": {"1": {"10": True}}}
        self.relay.save()

        local_time = datetime(2025, 1, 6, 10, 30, 0, tzinfo=dt_timezone(UTC.utcoffset(datetime.now(UTC))))
        with patch("odin.apps.relays.services.timezone.localtime", return_value=local_time):
            assert self.relay.target_state == RelayState.ON
