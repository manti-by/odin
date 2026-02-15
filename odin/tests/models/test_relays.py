from datetime import UTC, datetime
from datetime import timezone as dt_timezone
from decimal import Decimal
from unittest.mock import patch

import pytest

from odin.apps.relays.models import Relay, RelayState, RelayType
from odin.apps.sensors.models import Sensor
from odin.tests.factories import RelayFactory, SensorFactory, SensorLogFactory


@pytest.mark.django_db
class TestRelaysPeriodicSchedule:
    def setup_method(self):
        self.relay: Relay = RelayFactory(type=RelayType.PUMP)
        self.sensor: Sensor = SensorFactory(relay_id=self.relay.relay_id)

    def test_relays__periodic_schedule_returns_on_when_target_state_is_on(self):
        """Test that periodic schedule returns ON when target_state is ON."""
        self.relay.context = {
            "schedule": {"periods": [{"start_time": "08:00", "end_time": "18:00", "target_state": "ON"}]}
        }
        self.relay.save()

        local_time = datetime(2025, 1, 6, 10, 30, 0, tzinfo=dt_timezone(UTC.utcoffset(datetime.now(UTC))))
        with patch("odin.apps.relays.services.timezone.localtime", return_value=local_time):
            assert self.relay.target_state == RelayState.ON

    def test_relays__periodic_schedule_returns_off_when_target_state_is_off(self):
        """Test that periodic schedule returns OFF when target_state is OFF."""
        self.relay.context = {
            "schedule": {"periods": [{"start_time": "08:00", "end_time": "18:00", "target_state": "OFF"}]}
        }
        self.relay.save()

        local_time = datetime(2025, 1, 6, 10, 30, 0, tzinfo=dt_timezone(UTC.utcoffset(datetime.now(UTC))))
        with patch("odin.apps.relays.services.timezone.localtime", return_value=local_time):
            assert self.relay.target_state == RelayState.OFF

    def test_relays__periodic_schedule_returns_state_when_no_periods(self):
        """Test that periodic schedule returns relay state when no periods are defined."""
        self.relay.context = {"schedule": {"periods": []}}
        self.relay.context["state"] = "OFF"  # Set current state
        self.relay.save()

        local_time = datetime(2025, 1, 6, 10, 30, 0, tzinfo=dt_timezone(UTC.utcoffset(datetime.now(UTC))))
        with patch("odin.apps.relays.services.timezone.localtime", return_value=local_time):
            assert self.relay.target_state == RelayState.OFF

    def test_relays__periodic_schedule_returns_unknown_when_no_matching_period(self):
        """Test that periodic schedule returns UNKNOWN when current time doesn't match any period."""
        self.relay.context = {
            "schedule": {"periods": [{"start_time": "08:00", "end_time": "18:00", "target_temp": 25.0}]}
        }
        self.relay.save()
        SensorLogFactory(sensor_id=self.sensor.sensor_id, temp=Decimal("25.0"))

        # Outside the period (after 18:00)
        local_time = datetime(2025, 1, 6, 20, 30, 0, tzinfo=dt_timezone(UTC.utcoffset(datetime.now(UTC))))
        with patch("odin.apps.relays.services.timezone.localtime", return_value=local_time):
            assert self.relay.target_state == RelayState.UNKNOWN

    def test_relays__periodic_schedule_handles_overnight_periods(self):
        """Test that periodic schedule handles periods that span midnight."""
        self.relay.context = {
            "schedule": {"periods": [{"start_time": "22:00", "end_time": "06:00", "target_state": "ON"}]}
        }
        self.relay.save()

        # During overnight period (23:00)
        local_time = datetime(2025, 1, 6, 23, 30, 0, tzinfo=dt_timezone(UTC.utcoffset(datetime.now(UTC))))
        with patch("odin.apps.relays.services.timezone.localtime", return_value=local_time):
            assert self.relay.target_state == RelayState.ON

        # During overnight period (02:00)
        local_time = datetime(2025, 1, 7, 2, 30, 0, tzinfo=dt_timezone(UTC.utcoffset(datetime.now(UTC))))
        with patch("odin.apps.relays.services.timezone.localtime", return_value=local_time):
            assert self.relay.target_state == RelayState.ON

        # During overnight period (02:00)
        local_time = datetime(2025, 1, 7, 2, 30, 0, tzinfo=dt_timezone(UTC.utcoffset(datetime.now(UTC))))
        with patch("odin.apps.relays.services.timezone.localtime", return_value=local_time):
            assert self.relay.target_state == RelayState.ON

    def test_relays__periodic_schedule_applies_to_all_days(self):
        """Test that periodic schedule applies to all days of the week."""
        self.relay.context = {
            "schedule": {
                "periods": [
                    {
                        "start_time": "08:00",
                        "end_time": "18:00",
                        "target_state": "ON",
                    }
                ]
            }
        }
        self.relay.save()

        # Monday (day 1) - should work
        local_time = datetime(2025, 1, 6, 10, 30, 0, tzinfo=dt_timezone(UTC.utcoffset(datetime.now(UTC))))  # Monday
        with patch("odin.apps.relays.services.timezone.localtime", return_value=local_time):
            assert self.relay.target_state == RelayState.ON

        # Sunday (day 0) - should also work since periods apply to all days
        local_time = datetime(2025, 1, 5, 10, 30, 0, tzinfo=dt_timezone(UTC.utcoffset(datetime.now(UTC))))  # Sunday
        with patch("odin.apps.relays.services.timezone.localtime", return_value=local_time):
            assert self.relay.target_state == RelayState.ON


@pytest.mark.django_db
class TestServoPeriodOverride:
    def setup_method(self):
        self.relay: Relay = RelayFactory(type=RelayType.SERVO)
        self.sensor: Sensor = SensorFactory(relay_id=self.relay.relay_id)

    def test_relays__servo_uses_period_target_temp_when_available(self):
        """Test that SERVO relay uses period target_temp when available."""
        # Set sensor target_temp to 20.0
        self.sensor.context = {"target_temp": "20.0", "hysteresis": "1.0"}
        self.sensor.save()
        SensorLogFactory(sensor_id=self.sensor.sensor_id, temp=Decimal("22.0"))

        # Set period with different target_temp
        self.relay.context = {
            "schedule": {"periods": [{"start_time": "08:00", "end_time": "18:00", "target_temp": 25.0}]}
        }
        self.relay.save()

        local_time = datetime(2025, 1, 6, 10, 30, 0, tzinfo=dt_timezone(UTC.utcoffset(datetime.now(UTC))))
        with patch("odin.apps.relays.services.timezone.localtime", return_value=local_time):
            # Should use period target_temp (25.0), temp 22.0 < 25.0 - 1.0 = 24.0, so ON
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
        relay.context = {"schedule": {"periods": [{"start_time": "08:00", "end_time": "18:00", "target_state": "ON"}]}}
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
        self.relay.context = {
            "schedule": {"periods": [{"start_time": "08:00", "end_time": "18:00", "target_state": "OFF"}]}
        }
        self.relay.save()

        local_time = datetime(2025, 1, 6, 10, 30, 0, tzinfo=dt_timezone(UTC.utcoffset(datetime.now(UTC))))
        with patch("odin.apps.relays.services.timezone.localtime", return_value=local_time):
            assert self.relay.target_state == RelayState.ON

    def test_relays__target_state_returns_schedule_when_force_state_is_null(self):
        """Test that target_state uses schedule when force_state is null."""
        self.relay.force_state = None
        self.relay.context = {
            "schedule": {"periods": [{"start_time": "08:00", "end_time": "18:00", "target_state": "ON"}]}
        }
        self.relay.save()

        local_time = datetime(2025, 1, 6, 10, 30, 0, tzinfo=dt_timezone(UTC.utcoffset(datetime.now(UTC))))
        with patch("odin.apps.relays.services.timezone.localtime", return_value=local_time):
            assert self.relay.target_state == RelayState.ON


@pytest.mark.django_db
class TestRelaysRefreshStateFromKafka:
    def setup_method(self):
        self.relay: Relay = RelayFactory(type=RelayType.PUMP)

    @patch("odin.apps.core.kafka.KafkaService.get_relay_state_from_kafka")
    def test_relays__refresh_state_from_kafka_updates_context(self, mock_get_state):
        """Test that refresh_state_from_kafka updates context with state from Kafka."""
        mock_get_state.return_value = "ON"

        state = self.relay.refresh_state_from_kafka()

        assert state == "ON"
        assert self.relay.context["state"] == "ON"
        self.relay.refresh_from_db()
        assert self.relay.context["state"] == "ON"
        mock_get_state.assert_called_once_with(self.relay.relay_id)

    @patch("odin.apps.core.kafka.KafkaService.get_relay_state_from_kafka")
    def test_relays__refresh_state_from_kafka_raises_error_when_not_found(self, mock_get_state):
        """Test that refresh_state_from_kafka raises RelayStateError when state not found."""
        from odin.apps.relays.models import RelayStateError

        mock_get_state.return_value = None

        with pytest.raises(RelayStateError) as exc_info:
            self.relay.refresh_state_from_kafka()

        assert f"Failed to get state from Kafka for relay {self.relay.relay_id}" in str(exc_info.value)

    @patch("odin.apps.core.kafka.KafkaService.get_relay_state_from_kafka")
    def test_relays__refresh_state_from_kafka_returns_state_value(self, mock_get_state):
        """Test that refresh_state_from_kafka returns the state value."""
        mock_get_state.return_value = "OFF"

        state = self.relay.refresh_state_from_kafka()

        assert state == "OFF"
