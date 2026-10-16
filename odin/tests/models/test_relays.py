from datetime import UTC, datetime, timedelta
from datetime import timezone as dt_timezone
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from django.utils import timezone

from odin.apps.relays.models import Relay, RelayMode, RelayState, RelayType
from odin.apps.sensors.models import Sensor
from odin.tests.factories import RelayFactory, SensorFactory, SensorLogFactory, WeatherFactory


# Odd hour, minute 30: a time that never falls inside the 30-minute schedule cycle window
OUTSIDE_CYCLE_WINDOW = datetime(2025, 1, 6, 10, 30, 0, tzinfo=dt_timezone(UTC.utcoffset(datetime.now(UTC))))


@pytest.fixture(autouse=True)
def pin_clock_outside_cycle_window():
    """Keep the schedule branch out of the cycle window unless a test says otherwise.

    The cycle fires on every even hour for its first 30 minutes, so any test that reaches the
    schedule branch without pinning the clock would otherwise depend on when the suite runs.
    Tests that assert the cycle itself patch `timezone.localtime` themselves.
    """
    with patch("odin.apps.relays.services.timezone.localtime", return_value=OUTSIDE_CYCLE_WINDOW):
        yield


@pytest.mark.django_db
class TestRelaysPeriodicSchedule:
    def setup_method(self):
        self.relay: Relay = RelayFactory(type=RelayType.PUMP)
        self.sensor: Sensor = SensorFactory(relay=self.relay)

    def test_relays__periodic_schedule_returns_on_when_target_state_is_on(self):
        """Test that periodic schedule returns ON when target_state is ON."""
        self.relay.context = {
            "schedule": {"periods": [{"start_time": "08:00", "end_time": "18:00", "target_state": "ON"}]}
        }
        self.relay.save()

        local_time = datetime(2025, 1, 6, 10, 30, 0, tzinfo=dt_timezone(UTC.utcoffset(datetime.now(UTC))))
        with patch("odin.apps.relays.services.timezone.localtime", return_value=local_time):
            state, mode = self.relay.get_target_state()
            assert state == RelayState.ON
            assert mode == RelayMode.BASIC

    def test_relays__periodic_schedule_returns_off_when_target_state_is_off(self):
        """Test that periodic schedule returns OFF when target_state is OFF."""
        self.relay.context = {
            "schedule": {"periods": [{"start_time": "08:00", "end_time": "18:00", "target_state": "OFF"}]}
        }
        self.relay.save()

        local_time = datetime(2025, 1, 6, 10, 30, 0, tzinfo=dt_timezone(UTC.utcoffset(datetime.now(UTC))))
        with patch("odin.apps.relays.services.timezone.localtime", return_value=local_time):
            state, mode = self.relay.get_target_state()
            assert state == RelayState.OFF
            assert mode == RelayMode.BASIC

    def test_relays__periodic_schedule_returns_on_when_no_periods(self):
        """Test that periodic schedule defaults to ON when no periods are defined."""
        self.relay.context = {"schedule": {"periods": []}}
        self.relay.save()

        local_time = datetime(2025, 1, 6, 10, 30, 0, tzinfo=dt_timezone(UTC.utcoffset(datetime.now(UTC))))
        with patch("odin.apps.relays.services.timezone.localtime", return_value=local_time):
            state, mode = self.relay.get_target_state()
            assert state == RelayState.ON
            assert mode == RelayMode.FALLBACK

    def test_relays__periodic_schedule_returns_on_when_no_matching_period(self):
        """Test that periodic schedule defaults to ON when current time doesn't match any period."""
        self.relay.context = {
            "schedule": {"periods": [{"start_time": "08:00", "end_time": "18:00", "target_temp": 25.0}]}
        }
        self.relay.save()
        SensorLogFactory(sensor=self.sensor, temp=Decimal("25.0"))

        # Outside the period (after 18:00)
        local_time = datetime(2025, 1, 6, 20, 30, 0, tzinfo=dt_timezone(UTC.utcoffset(datetime.now(UTC))))
        with patch("odin.apps.relays.services.timezone.localtime", return_value=local_time):
            state, mode = self.relay.get_target_state()
            assert state == RelayState.ON
            assert mode == RelayMode.FALLBACK

    def test_relays__periodic_schedule_end_time_belongs_to_next_period(self):
        """Test that a period's end time is exclusive, so adjacent periods do not overlap."""
        self.relay.context = {
            "schedule": {
                "periods": [
                    {"start_time": "07:00", "end_time": "11:00", "target_state": "ON"},
                    {"start_time": "11:00", "end_time": "15:00", "target_state": "OFF"},
                ]
            }
        }
        self.relay.save()

        # 11:00 is an odd hour, so the boundary cannot be masked by the schedule cycle
        local_time = datetime(2025, 1, 6, 11, 0, 0, tzinfo=dt_timezone(UTC.utcoffset(datetime.now(UTC))))
        with patch("odin.apps.relays.services.timezone.localtime", return_value=local_time):
            state, mode = self.relay.get_target_state()
            assert state == RelayState.OFF
            assert mode == RelayMode.BASIC

    def test_relays__periodic_schedule_handles_overnight_periods(self):
        """Test that periodic schedule handles periods that span midnight."""
        self.relay.context = {
            "schedule": {"periods": [{"start_time": "22:00", "end_time": "06:00", "target_state": "ON"}]}
        }
        self.relay.save()

        # During overnight period (23:00)
        local_time = datetime(2025, 1, 6, 23, 30, 0, tzinfo=dt_timezone(UTC.utcoffset(datetime.now(UTC))))
        with patch("odin.apps.relays.services.timezone.localtime", return_value=local_time):
            state, mode = self.relay.get_target_state()
            assert state == RelayState.ON
            assert mode == RelayMode.BASIC

        # During overnight period (02:00)
        local_time = datetime(2025, 1, 7, 2, 30, 0, tzinfo=dt_timezone(UTC.utcoffset(datetime.now(UTC))))
        with patch("odin.apps.relays.services.timezone.localtime", return_value=local_time):
            state, mode = self.relay.get_target_state()
            assert state == RelayState.ON
            assert mode == RelayMode.BASIC

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
            state, mode = self.relay.get_target_state()
            assert state == RelayState.ON
            assert mode == RelayMode.BASIC

        # Sunday (day 0) - should also work since periods apply to all days
        local_time = datetime(2025, 1, 5, 10, 30, 0, tzinfo=dt_timezone(UTC.utcoffset(datetime.now(UTC))))  # Sunday
        with patch("odin.apps.relays.services.timezone.localtime", return_value=local_time):
            state, mode = self.relay.get_target_state()
            assert state == RelayState.ON
            assert mode == RelayMode.BASIC


@pytest.mark.django_db
class TestServoPeriodOverride:
    def setup_method(self):
        self.relay: Relay = RelayFactory(type=RelayType.SERVO)
        self.sensor: Sensor = SensorFactory(relay=self.relay)

    def test_relays__servo_uses_period_target_temp_when_available(self):
        """Test that SERVO relay uses period target_temp when available."""
        # Set sensor target_temp to 20.0
        self.sensor.context = {"target_temp": "20.0", "hysteresis": "1.0"}
        self.sensor.save()
        SensorLogFactory(sensor=self.sensor, temp=Decimal("22.0"), created_at=timezone.now())

        # Set period with different target_temp
        self.relay.context = {
            "schedule": {"periods": [{"start_time": "08:00", "end_time": "18:00", "target_temp": 25.0}]}
        }
        self.relay.save()

        local_time = datetime(2025, 1, 6, 10, 30, 0, tzinfo=dt_timezone(UTC.utcoffset(datetime.now(UTC))))
        with patch("odin.apps.relays.services.timezone.localtime", return_value=local_time):
            # Should use period target_temp (25.0), temp 22.0 < 25.0 - 1.0 = 24.0, so OFF
            state, mode = self.relay.get_target_state()
            assert state == RelayState.OFF
            assert mode == RelayMode.BASIC

    def test_relays__servo_uses_zero_period_target_temp(self):
        """Test that a period target_temp of 0 is honored instead of the sensor default."""
        self.sensor.context = {"target_temp": "20.0", "hysteresis": "1.0"}
        self.sensor.save()
        SensorLogFactory(sensor=self.sensor, temp=Decimal("10.0"), created_at=timezone.now())

        self.relay.context = {"schedule": {"periods": [{"start_time": "08:00", "end_time": "18:00", "target_temp": 0}]}}
        self.relay.save()

        local_time = datetime(2025, 1, 6, 10, 30, 0, tzinfo=dt_timezone(UTC.utcoffset(datetime.now(UTC))))
        with patch("odin.apps.relays.services.timezone.localtime", return_value=local_time):
            # 10.0 > 0 + 1.0, so the circuit opens instead of regulating against the sensor's 20.0
            state, mode = self.relay.get_target_state()
            assert state == RelayState.ON
            assert mode == RelayMode.BASIC


@pytest.mark.django_db
class TestRelaysSensorProperty:
    def setup_method(self):
        self.relay: Relay = RelayFactory()  # noqa

    def test_relays__sensor_returns_none_when_no_linked_sensor(self):
        """Test that sensor property returns None when no sensor is linked."""
        assert self.relay.sensor is None

    def test_relays__sensor_returns_linked_sensor(self):
        """Test that sensor property returns the linked sensor."""
        sensor = SensorFactory(relay=self.relay)
        assert self.relay.sensor == sensor

    def test_relays__sensor_returns_most_recent_when_multiple(self):
        """Test that sensor property returns the most recent sensor."""
        SensorFactory(relay=self.relay)
        new_sensor = SensorFactory(relay=self.relay)
        assert self.relay.sensor == new_sensor


@pytest.mark.django_db
class TestRelaysServoTargetState:
    def setup_method(self):
        self.relay: Relay = RelayFactory(type=RelayType.SERVO)  # noqa
        self.sensor: Sensor = SensorFactory(relay=self.relay)  # noqa

    def test_relays__servo_target_state_returns_off_when_no_sensor(self):
        """Test that target_state opens the circuit when there is no linked sensor."""
        self.sensor.relay = None
        self.sensor.save(update_fields=["relay"])
        state, mode = self.relay.get_target_state()
        assert state == RelayState.OFF
        assert mode == RelayMode.UNKNOWN

    def test_relays__servo_target_state_returns_off_when_sensor_is_stale(self):
        """Test that target_state opens the circuit when the sensor stopped reporting."""
        self.sensor.context = {"target_temp": "25.0", "hysteresis": "1.0"}
        self.sensor.save()
        Sensor.objects.filter(pk=self.sensor.pk).update(updated_at=timezone.now() - timedelta(minutes=30))
        self.sensor.refresh_from_db()

        state, mode = self.relay.get_target_state()
        assert state == RelayState.OFF
        assert mode == RelayMode.UNKNOWN

    def test_relays__servo_target_state_returns_off_when_temp_below_min(self):
        """Test that servo turns OFF when temp is below target - hysteresis."""
        self.sensor.context = {"target_temp": "25.0", "hysteresis": "1.0"}
        self.sensor.save()
        SensorLogFactory(sensor=self.sensor, temp=Decimal("23.0"), created_at=timezone.now())

        state, mode = self.relay.get_target_state()
        assert state == RelayState.OFF
        assert mode == RelayMode.BASIC

    def test_relays__servo_target_state_returns_on_when_temp_above_max(self):
        """Test that servo turns ON when temp is above target plus hysteresis."""
        self.sensor.context = {"target_temp": "25.0", "hysteresis": "1.0"}
        self.sensor.save()
        SensorLogFactory(sensor=self.sensor, temp=Decimal("27.0"), created_at=timezone.now())

        state, mode = self.relay.get_target_state()
        assert state == RelayState.ON
        assert mode == RelayMode.BASIC

    def test_relays__servo_target_state_returns_off_when_temp_in_range(self):
        """Test that servo turns OFF when temp is within hysteresis range."""
        self.sensor.context = {"target_temp": "25.0", "hysteresis": "1.0"}
        self.sensor.save()
        SensorLogFactory(sensor=self.sensor, temp=Decimal("25.0"), created_at=timezone.now())

        state, mode = self.relay.get_target_state()
        assert state == RelayState.OFF
        assert mode == RelayMode.FALLBACK

    def test_relays__servo_target_state_returns_off_when_no_temp(self):
        """Test that target_state opens the circuit when sensor has no temperature reading."""
        self.sensor.context = {"target_temp": "25.0", "hysteresis": "1.0"}
        self.sensor.save()

        state, mode = self.relay.get_target_state()
        assert state == RelayState.OFF
        assert mode == RelayMode.UNKNOWN

    def test_relays__servo_target_state_returns_off_when_no_target_temp(self):
        """Test that target_state opens the circuit when no target_temp is configured (no crash)."""
        self.sensor.context = {"hysteresis": "1.0"}
        self.sensor.save()
        SensorLogFactory(sensor=self.sensor, temp=Decimal("23.0"), created_at=timezone.now())

        state, mode = self.relay.get_target_state()
        assert state == RelayState.OFF
        assert mode == RelayMode.UNKNOWN


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
            state, mode = relay.get_target_state()
            assert state == RelayState.ON
            assert mode == RelayMode.BASIC

    def test_relays__target_state_returns_servo_state_for_servo_type(self):
        """Test that target_state uses target_state for SERVO type."""
        relay: Relay = RelayFactory(type=RelayType.SERVO)  # noqa
        sensor: Sensor = SensorFactory(relay=relay)  # noqa
        sensor.context = {"target_temp": "25.0", "hysteresis": "1.0"}
        sensor.save()
        SensorLogFactory(sensor=sensor, temp=Decimal("23.0"), created_at=timezone.now())

        state, mode = relay.get_target_state()
        assert state == RelayState.OFF
        assert mode == RelayMode.BASIC

    def test_relays__target_state_returns_unknown_for_unknown_type(self):
        """Test that target_state returns UNKNOWN for unknown relay types."""
        relay: Relay = RelayFactory(type=RelayType.VALVE)  # noqa
        state, mode = relay.get_target_state()
        assert state == RelayState.UNKNOWN
        assert mode == RelayMode.FALLBACK


@pytest.mark.django_db
class TestRelaysWeatherModes:
    def test_relays__pump_is_off_in_summer(self):
        """Test that a PUMP is off when outside temperature is 15°C or higher."""
        relay: Relay = RelayFactory(type=RelayType.PUMP)  # noqa
        WeatherFactory(period=timezone.now(), data={"temp": {"avg": "20.0"}})

        state, mode = relay.get_target_state()
        assert state == RelayState.OFF
        assert mode == RelayMode.SUMMER

    def test_relays__pump_is_on_in_antifreeze(self):
        """Test that a PUMP runs continuously below -8°C."""
        relay: Relay = RelayFactory(type=RelayType.PUMP)  # noqa
        WeatherFactory(period=timezone.now(), data={"temp": {"avg": "-10.0"}})

        state, mode = relay.get_target_state()
        assert state == RelayState.ON
        assert mode == RelayMode.ANTIFREEZE

    def test_relays__pump_runs_first_half_hour_of_every_second_hour_in_midseason(self):
        """Test that a PUMP runs for the first 30 minutes of every 2-hour window in midseason."""
        relay: Relay = RelayFactory(type=RelayType.PUMP)  # noqa
        WeatherFactory(period=timezone.now(), data={"temp": {"avg": "10.0"}})

        local_time = datetime(2025, 1, 6, 8, 5, 0, tzinfo=dt_timezone(UTC.utcoffset(datetime.now(UTC))))
        with patch("odin.apps.relays.services.timezone.localtime", return_value=local_time):
            state, mode = relay.get_target_state()
            assert state == RelayState.ON
            assert mode == RelayMode.MIDSEASON

    def test_relays__pump_is_off_outside_every_second_hour_in_midseason(self):
        """Test that a PUMP is off during the idle hour and the second half of every 2-hour window."""
        relay: Relay = RelayFactory(type=RelayType.PUMP)  # noqa
        WeatherFactory(period=timezone.now(), data={"temp": {"avg": "10.0"}})

        local_time = datetime(2025, 1, 6, 8, 45, 0, tzinfo=dt_timezone(UTC.utcoffset(datetime.now(UTC))))
        with patch("odin.apps.relays.services.timezone.localtime", return_value=local_time):
            state, mode = relay.get_target_state()
            assert state == RelayState.OFF
            assert mode == RelayMode.MIDSEASON
        with patch("odin.apps.relays.services.timezone.localtime", return_value=local_time):
            state, mode = relay.get_target_state()
            assert state == RelayState.OFF
            assert mode == RelayMode.MIDSEASON

    def test_relays__servo_stays_open_in_summer(self):
        """Test that a SERVO stays open (OFF) when outside temperature is 15°C or higher."""
        relay: Relay = RelayFactory(type=RelayType.SERVO)  # noqa
        sensor: Sensor = SensorFactory(relay=relay)  # noqa
        sensor.context = {"target_temp": "25.0", "hysteresis": "1.0"}
        sensor.save()
        SensorLogFactory(sensor=sensor, temp=Decimal("23.0"), created_at=timezone.now())
        WeatherFactory(period=timezone.now(), data={"temp": {"avg": "20.0"}})

        state, mode = relay.get_target_state()
        assert state == RelayState.OFF
        assert mode == RelayMode.SUMMER

    def test_relays__servo_stays_open_in_antifreeze(self):
        """Test that a SERVO stays open (OFF) below -8°C."""
        relay: Relay = RelayFactory(type=RelayType.SERVO)  # noqa
        sensor: Sensor = SensorFactory(relay=relay)  # noqa
        sensor.context = {"target_temp": "25.0", "hysteresis": "1.0"}
        sensor.save()
        SensorLogFactory(sensor=sensor, temp=Decimal("23.0"), created_at=timezone.now())
        WeatherFactory(period=timezone.now(), data={"temp": {"avg": "-10.0"}})

        state, mode = relay.get_target_state()
        assert state == RelayState.OFF
        assert mode == RelayMode.ANTIFREEZE

    def test_relays__servo_stays_open_in_first_half_hour_of_every_second_hour_in_midseason(self):
        """Test that a SERVO stays open (OFF) in midseason."""
        relay: Relay = RelayFactory(type=RelayType.SERVO)  # noqa
        sensor: Sensor = SensorFactory(relay=relay)  # noqa
        sensor.context = {"target_temp": "25.0", "hysteresis": "1.0"}
        sensor.save()
        SensorLogFactory(sensor=sensor, temp=Decimal("23.0"), created_at=timezone.now())
        WeatherFactory(period=timezone.now(), data={"temp": {"avg": "10.0"}})

        local_time = datetime(2025, 1, 6, 8, 5, 0, tzinfo=dt_timezone(UTC.utcoffset(datetime.now(UTC))))
        with patch("odin.apps.relays.services.timezone.localtime", return_value=local_time):
            state, mode = relay.get_target_state()
            assert state == RelayState.OFF
            assert mode == RelayMode.MIDSEASON

    def test_relays__servo_stays_open_outside_every_second_hour_in_midseason(self):
        """Test that a SERVO stays open (OFF) during the idle hour and the second half of every 2-hour window."""
        relay: Relay = RelayFactory(type=RelayType.SERVO)  # noqa
        sensor: Sensor = SensorFactory(relay=relay)  # noqa
        sensor.context = {"target_temp": "25.0", "hysteresis": "1.0"}
        sensor.save()
        SensorLogFactory(sensor=sensor, temp=Decimal("23.0"), created_at=timezone.now())
        WeatherFactory(period=timezone.now(), data={"temp": {"avg": "10.0"}})

        local_time = datetime(2025, 1, 6, 8, 45, 0, tzinfo=dt_timezone(UTC.utcoffset(datetime.now(UTC))))
        with patch("odin.apps.relays.services.timezone.localtime", return_value=local_time):
            state, mode = relay.get_target_state()
            assert state == RelayState.OFF
            assert mode == RelayMode.MIDSEASON

    @pytest.mark.parametrize(
        ("hour", "expected_state"),
        (
            (0, RelayState.OFF),
            (3, RelayState.OFF),
            (5, RelayState.OFF),
            (6, RelayState.ON),
            (7, RelayState.OFF),
            (9, RelayState.OFF),
            (20, RelayState.ON),
            (21, RelayState.OFF),
            (23, RelayState.OFF),
        ),
    )
    def test_relays__pump_midseason_cadence_by_hour(self, hour, expected_state):
        """Verify a PUMP runs only in the first 30 minutes of even daytime hours (hour >= 6) in midseason."""
        relay: Relay = RelayFactory(type=RelayType.PUMP)  # noqa
        WeatherFactory(period=timezone.now(), data={"temp": {"avg": "10.0"}})

        local_time = datetime(2025, 1, 6, hour, 5, 0, tzinfo=dt_timezone(UTC.utcoffset(datetime.now(UTC))))
        with patch("odin.apps.relays.services.timezone.localtime", return_value=local_time):
            state, mode = relay.get_target_state()
            assert state == expected_state
            assert mode == RelayMode.MIDSEASON

    @pytest.mark.parametrize(
        ("hour", "expected_state"),
        (
            (0, RelayState.OFF),
            (1, RelayState.OFF),
            (2, RelayState.OFF),
            (3, RelayState.OFF),
            (6, RelayState.OFF),
            (9, RelayState.OFF),
            (21, RelayState.OFF),
            (22, RelayState.OFF),
            (23, RelayState.OFF),
        ),
    )
    def test_relays__servo_midseason_cadence_by_hour(self, hour, expected_state):
        """Verify a SERVO stays open (OFF) at every hour in midseason."""
        relay: Relay = RelayFactory(type=RelayType.SERVO)  # noqa
        sensor: Sensor = SensorFactory(relay=relay)  # noqa
        sensor.context = {"target_temp": "25.0", "hysteresis": "1.0"}
        sensor.save()
        SensorLogFactory(sensor=sensor, temp=Decimal("23.0"), created_at=timezone.now())
        WeatherFactory(period=timezone.now(), data={"temp": {"avg": "10.0"}})

        local_time = datetime(2025, 1, 6, hour, 30, 0, tzinfo=dt_timezone(UTC.utcoffset(datetime.now(UTC))))
        with patch("odin.apps.relays.services.timezone.localtime", return_value=local_time):
            state, mode = relay.get_target_state()
            assert state == expected_state
            assert mode == RelayMode.MIDSEASON

    @pytest.mark.parametrize("minute", (0, 10, 29))
    def test_relays__pump_midseason_active_window_spans_first_half_hour(self, minute):
        """Verify the pump midseason window runs for the first 30 minutes of the active hour."""
        relay: Relay = RelayFactory(type=RelayType.PUMP)  # noqa
        WeatherFactory(period=timezone.now(), data={"temp": {"avg": "10.0"}})

        local_time = datetime(2025, 1, 6, 8, minute, 0, tzinfo=dt_timezone(UTC.utcoffset(datetime.now(UTC))))
        with patch("odin.apps.relays.services.timezone.localtime", return_value=local_time):
            state, mode = relay.get_target_state()
            assert state == RelayState.ON
            assert mode == RelayMode.MIDSEASON

    @pytest.mark.parametrize("minute", (30, 45, 59))
    def test_relays__pump_midseason_is_off_in_second_half_hour(self, minute):
        """Verify the pump midseason window stops after the first 30 minutes of the active hour."""
        relay: Relay = RelayFactory(type=RelayType.PUMP)  # noqa
        WeatherFactory(period=timezone.now(), data={"temp": {"avg": "10.0"}})

        local_time = datetime(2025, 1, 6, 8, minute, 0, tzinfo=dt_timezone(UTC.utcoffset(datetime.now(UTC))))
        with patch("odin.apps.relays.services.timezone.localtime", return_value=local_time):
            state, mode = relay.get_target_state()
            assert state == RelayState.OFF
            assert mode == RelayMode.MIDSEASON

    @pytest.mark.parametrize("minute", (0, 30, 59))
    def test_relays__servo_midseason_active_window_spans_full_hour(self, minute):
        """Verify the servo stays open for the whole active hour, not only its first 30 minutes."""
        relay: Relay = RelayFactory(type=RelayType.SERVO)  # noqa
        sensor: Sensor = SensorFactory(relay=relay)  # noqa
        sensor.context = {"target_temp": "25.0", "hysteresis": "1.0"}
        sensor.save()
        SensorLogFactory(sensor=sensor, temp=Decimal("23.0"), created_at=timezone.now())
        WeatherFactory(period=timezone.now(), data={"temp": {"avg": "10.0"}})

        local_time = datetime(2025, 1, 6, 8, minute, 0, tzinfo=dt_timezone(UTC.utcoffset(datetime.now(UTC))))
        with patch("odin.apps.relays.services.timezone.localtime", return_value=local_time):
            state, mode = relay.get_target_state()
            assert state == RelayState.OFF
            assert mode == RelayMode.MIDSEASON


@pytest.mark.django_db
class TestRelaysScheduleCycle:
    """MNT-250: the schedule branch forces the relay open for 30 minutes every 2 hours."""

    @staticmethod
    def _at(hour: int, minute: int) -> datetime:
        return datetime(2025, 1, 6, hour, minute, 0, tzinfo=dt_timezone(UTC.utcoffset(datetime.now(UTC))))

    @staticmethod
    def _pump(periods: list[dict] | None = None) -> Relay:
        relay: Relay = RelayFactory(type=RelayType.PUMP)  # noqa
        if periods is not None:
            relay.context = {"schedule": {"periods": periods}}
            relay.save()
        return relay

    @staticmethod
    def _servo(periods: list[dict] | None = None) -> Relay:
        relay: Relay = RelayFactory(type=RelayType.SERVO)  # noqa
        sensor: Sensor = SensorFactory(relay=relay)  # noqa
        sensor.context = {"target_temp": "25.0", "hysteresis": "1.0"}
        sensor.save()
        SensorLogFactory(sensor=sensor, temp=Decimal("23.0"), created_at=timezone.now())
        if periods is not None:
            relay.context = {"schedule": {"periods": periods}}
            relay.save()
        return relay

    def test_relays__pump_cycle_overrides_an_off_schedule_period(self):
        """The pump runs inside the window even when the schedule period says OFF."""
        relay = self._pump([{"start_time": "00:00", "end_time": "23:59", "target_state": "OFF"}])

        with patch("odin.apps.relays.services.timezone.localtime", return_value=self._at(8, 5)):
            state, mode = relay.get_target_state()
            assert state == RelayState.ON
            assert mode == RelayMode.CYCLE

    def test_relays__pump_cycle_applies_without_a_schedule(self):
        """The pump reports CYCLE instead of FALLBACK when no period matches."""
        relay = self._pump([{"start_time": "08:00", "end_time": "18:00", "target_state": "ON"}])

        with patch("odin.apps.relays.services.timezone.localtime", return_value=self._at(20, 5)):
            state, mode = relay.get_target_state()
            assert state == RelayState.ON
            assert mode == RelayMode.CYCLE

    def test_relays__pump_outside_the_window_follows_the_schedule(self):
        """Outside the window the pump is driven by the schedule period."""
        relay = self._pump([{"start_time": "00:00", "end_time": "23:59", "target_state": "OFF"}])

        with patch("odin.apps.relays.services.timezone.localtime", return_value=self._at(8, 45)):
            state, mode = relay.get_target_state()
            assert state == RelayState.OFF
            assert mode == RelayMode.BASIC

    def test_relays__pump_outside_the_window_falls_back_without_a_period(self):
        """Outside the window an unmatched period still yields the FALLBACK default."""
        relay = self._pump([{"start_time": "08:00", "end_time": "18:00", "target_state": "ON"}])

        with patch("odin.apps.relays.services.timezone.localtime", return_value=self._at(20, 45)):
            state, mode = relay.get_target_state()
            assert state == RelayState.ON
            assert mode == RelayMode.FALLBACK

    def test_relays__servo_cycle_opens_the_circuit_below_target_temp(self):
        """The servo opens inside the window instead of regulating towards the target temp."""
        relay = self._servo([{"start_time": "00:00", "end_time": "23:59", "target_temp": 25.0}])

        with patch("odin.apps.relays.services.timezone.localtime", return_value=self._at(8, 5)):
            state, mode = relay.get_target_state()
            assert state == RelayState.OFF
            assert mode == RelayMode.CYCLE

    def test_relays__servo_cycle_applies_without_a_schedule(self):
        """The servo reports CYCLE instead of FALLBACK when no period matches."""
        relay = self._servo([{"start_time": "08:00", "end_time": "18:00", "target_temp": 25.0}])

        with patch("odin.apps.relays.services.timezone.localtime", return_value=self._at(20, 5)):
            state, mode = relay.get_target_state()
            assert state == RelayState.OFF
            assert mode == RelayMode.CYCLE

    def test_relays__servo_outside_the_window_regulates_by_sensor(self):
        """Outside the window the servo regulates against the sensor again."""
        relay = self._servo([{"start_time": "00:00", "end_time": "23:59", "target_temp": 25.0}])

        with patch("odin.apps.relays.services.timezone.localtime", return_value=self._at(8, 45)):
            state, mode = relay.get_target_state()
            assert state == RelayState.ON
            assert mode == RelayMode.BASIC

    @pytest.mark.parametrize("hour", (0, 2, 4, 6, 8, 12, 18, 22))
    def test_relays__cycle_runs_at_every_even_hour_including_night(self, hour):
        """The cycle has no night guard: even hours are forced all around the clock."""
        relay = self._pump([{"start_time": "00:00", "end_time": "23:59", "target_state": "OFF"}])

        with patch("odin.apps.relays.services.timezone.localtime", return_value=self._at(hour, 5)):
            state, mode = relay.get_target_state()
            assert state == RelayState.ON
            assert mode == RelayMode.CYCLE

    @pytest.mark.parametrize("hour", (1, 3, 5, 7, 11, 13, 21, 23))
    def test_relays__cycle_is_off_on_odd_hours(self, hour):
        """Odd hours are never part of the cycle window."""
        relay = self._pump([{"start_time": "00:00", "end_time": "23:59", "target_state": "OFF"}])

        with patch("odin.apps.relays.services.timezone.localtime", return_value=self._at(hour, 5)):
            state, mode = relay.get_target_state()
            assert state == RelayState.OFF
            assert mode == RelayMode.BASIC

    @pytest.mark.parametrize("minute", (0, 10, 29))
    def test_relays__cycle_window_spans_the_first_half_hour(self, minute):
        relay = self._pump([{"start_time": "00:00", "end_time": "23:59", "target_state": "OFF"}])

        with patch("odin.apps.relays.services.timezone.localtime", return_value=self._at(8, minute)):
            state, mode = relay.get_target_state()
            assert state == RelayState.ON
            assert mode == RelayMode.CYCLE

    @pytest.mark.parametrize("minute", (30, 45, 59))
    def test_relays__cycle_window_ends_after_the_first_half_hour(self, minute):
        relay = self._pump([{"start_time": "00:00", "end_time": "23:59", "target_state": "OFF"}])

        with patch("odin.apps.relays.services.timezone.localtime", return_value=self._at(8, minute)):
            state, mode = relay.get_target_state()
            assert state == RelayState.OFF
            assert mode == RelayMode.BASIC

    def test_relays__cycle_applies_without_weather_data(self):
        """The rule is time based, so missing weather must not disable it."""
        relay = self._pump([{"start_time": "00:00", "end_time": "23:59", "target_state": "OFF"}])

        with patch("odin.apps.relays.services.timezone.localtime", return_value=self._at(8, 5)):
            state, mode = relay.get_target_state()
            assert state == RelayState.ON
            assert mode == RelayMode.CYCLE

    @pytest.mark.parametrize(
        ("temp", "expected_mode"),
        (
            ("15.0", RelayMode.SUMMER),
            ("8.1", RelayMode.MIDSEASON),
            ("8.0", RelayMode.CYCLE),
            ("-8.1", RelayMode.ANTIFREEZE),
            ("-8.0", RelayMode.CYCLE),
        ),
    )
    def test_relays__cycle_does_not_leak_into_other_temperature_bands(self, temp, expected_mode):
        """Band edges keep their existing boundaries: the cycle only fills the gap below midseason."""
        relay = self._pump([{"start_time": "00:00", "end_time": "23:59", "target_state": "OFF"}])
        WeatherFactory(period=timezone.now(), data={"temp": {"avg": temp}})

        with patch("odin.apps.relays.services.timezone.localtime", return_value=self._at(8, 5)):
            _, mode = relay.get_target_state()
            assert mode == expected_mode

    def test_relays__midseason_still_wins_over_the_cycle_at_night(self):
        """Midseason keeps its own night guard: 03:05 is OFF/MIDSEASON, not ON/CYCLE."""
        relay = self._pump([{"start_time": "00:00", "end_time": "23:59", "target_state": "ON"}])
        WeatherFactory(period=timezone.now(), data={"temp": {"avg": "10.0"}})

        with patch("odin.apps.relays.services.timezone.localtime", return_value=self._at(3, 5)):
            state, mode = relay.get_target_state()
            assert state == RelayState.OFF
            assert mode == RelayMode.MIDSEASON

    def test_relays__force_state_still_wins_over_the_cycle(self):
        relay = self._pump([{"start_time": "00:00", "end_time": "23:59", "target_state": "ON"}])
        relay.force_state = RelayState.OFF
        relay.save()

        with patch("odin.apps.relays.services.timezone.localtime", return_value=self._at(8, 5)):
            state, mode = relay.get_target_state()
            assert state == RelayState.OFF
            assert mode == RelayMode.FORCED

    def test_relays__dead_sensor_servo_still_reports_unknown_instead_of_cycle(self):
        relay = self._servo([{"start_time": "00:00", "end_time": "23:59", "target_temp": 25.0}])
        Sensor.objects.filter(pk=relay.sensor.pk).update(updated_at=timezone.now() - timedelta(minutes=30))
        relay.sensor.refresh_from_db()

        with patch("odin.apps.relays.services.timezone.localtime", return_value=self._at(8, 5)):
            state, mode = relay.get_target_state()
            assert state == RelayState.OFF
            assert mode == RelayMode.UNKNOWN

    def test_relays__servo_with_off_pump_still_reports_ignored_instead_of_cycle(self):
        pump: Relay = RelayFactory(type=RelayType.PUMP, state=RelayState.OFF)  # noqa
        relay = self._servo([{"start_time": "00:00", "end_time": "23:59", "target_temp": 25.0}])
        relay.related_relay = pump
        relay.save()

        with patch("odin.apps.relays.services.timezone.localtime", return_value=self._at(8, 5)):
            state, mode = relay.get_target_state()
            assert state == RelayState.OFF
            assert mode == RelayMode.IGNORED


@pytest.mark.django_db
class TestRelaysForceState:
    def setup_method(self):
        self.relay: Relay = RelayFactory(type=RelayType.PUMP)  # noqa

    def test_relays__target_state_returns_force_state_when_set_to_on(self):
        """Test that target_state returns force_state when set to ON."""
        self.relay.force_state = RelayState.ON
        self.relay.save()
        state, mode = self.relay.get_target_state()
        assert state == RelayState.ON
        assert mode == RelayMode.FORCED

    def test_relays__target_state_returns_force_state_when_set_to_off(self):
        """Test that target_state returns force_state when set to OFF."""
        self.relay.force_state = RelayState.OFF
        self.relay.save()
        state, mode = self.relay.get_target_state()
        assert state == RelayState.OFF
        assert mode == RelayMode.FORCED

    def test_relays__target_state_ignores_schedule_when_force_state_set(self):
        """Test that target_state ignores schedule when force_state is set."""
        self.relay.force_state = RelayState.ON
        self.relay.context = {
            "schedule": {"periods": [{"start_time": "08:00", "end_time": "18:00", "target_state": "OFF"}]}
        }
        self.relay.save()

        local_time = datetime(2025, 1, 6, 10, 30, 0, tzinfo=dt_timezone(UTC.utcoffset(datetime.now(UTC))))
        with patch("odin.apps.relays.services.timezone.localtime", return_value=local_time):
            state, mode = self.relay.get_target_state()
            assert state == RelayState.ON
            assert mode == RelayMode.FORCED

    def test_relays__target_state_returns_schedule_when_force_state_is_null(self):
        """Test that target_state uses schedule when force_state is null."""
        self.relay.force_state = None
        self.relay.context = {
            "schedule": {"periods": [{"start_time": "08:00", "end_time": "18:00", "target_state": "ON"}]}
        }
        self.relay.save()

        local_time = datetime(2025, 1, 6, 10, 30, 0, tzinfo=dt_timezone(UTC.utcoffset(datetime.now(UTC))))
        with patch("odin.apps.relays.services.timezone.localtime", return_value=local_time):
            state, mode = self.relay.get_target_state()
            assert state == RelayState.ON
            assert mode == RelayMode.BASIC


@pytest.mark.django_db
class TestRelaysRefreshState:
    def setup_method(self):
        self.relay: Relay = RelayFactory(type=RelayType.PUMP)

    @patch("odin.apps.core.redis_bus.RedisBus.get_relay_latest_message")
    def test_relays__refresh_state_updates_state(self, mock_get_state):
        """Test that refresh_state updates the state field from Redis."""
        mock_get_state.return_value = {"data": {"state": "ON"}}

        state = self.relay.refresh_state()

        assert state == "ON"
        assert self.relay.state == "ON"
        self.relay.refresh_from_db()
        assert self.relay.state == "ON"
        mock_get_state.assert_called_once_with(self.relay.relay_id)

    @patch("odin.apps.core.redis_bus.RedisBus.get_relay_latest_message")
    def test_relays__refresh_state_updates_mode(self, mock_get_state):
        """Test that refresh_state applies the mode reported alongside the state."""
        mock_get_state.return_value = {"data": {"state": "OFF", "mode": RelayMode.MIDSEASON.value}}

        state = self.relay.refresh_state()

        assert state == "OFF"
        self.relay.refresh_from_db()
        assert self.relay.mode == RelayMode.MIDSEASON

    @patch("odin.apps.core.redis_bus.RedisBus.get_relay_latest_message")
    def test_relays__refresh_state_ignores_missing_or_invalid_mode(self, mock_get_state: MagicMock) -> None:
        """A payload without a known mode leaves the stored mode untouched."""
        mock_get_state.return_value = {"data": {"state": "OFF"}}
        assert self.relay.refresh_state() == "OFF"
        self.relay.refresh_from_db()
        assert self.relay.mode is None

        mock_get_state.return_value = {"data": {"state": "ON", "mode": "NONSENSE"}}
        assert self.relay.refresh_state() == "ON"
        self.relay.refresh_from_db()
        assert self.relay.mode is None

    @patch("odin.apps.core.redis_bus.RedisBus.get_relay_latest_message")
    def test_relays__get_relay_data_raises_error_when_not_found(self, mock_get_state: MagicMock) -> None:
        """Test that refresh_state returns None when relay state is missing."""
        mock_get_state.return_value = None
        assert self.relay.refresh_state() is None

    @patch("odin.apps.core.redis_bus.RedisBus.get_relay_latest_message")
    def test_relays__get_relay_data_returns_state_value(self, mock_get_state):
        """Test that refresh_state returns the state value."""
        mock_get_state.return_value = {"data": {"state": "OFF"}}

        state = self.relay.refresh_state()
        assert state == "OFF"
