from datetime import UTC, datetime, timedelta
from datetime import timezone as dt_timezone
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from django.utils import timezone

from odin.apps.relays.models import Relay, RelayMode, RelayState, RelayType
from odin.apps.sensors.models import Sensor
from odin.tests.factories import RelayFactory, SensorFactory, SensorLogFactory, WeatherFactory


pytestmark = pytest.mark.usefixtures("pin_clock_outside_cycle_window")


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

    def test_relays__periodic_schedule_skips_malformed_periods(self):
        """Test that hand-edited or non-dict periods are skipped instead of raising."""
        self.relay.context = {
            "schedule": {
                "periods": [
                    {"start_time": None, "end_time": "18:00", "target_state": "OFF"},
                    {"start_time": "08:00", "end_time": "18:00", "target_state": "ON"},
                ]
            }
        }
        self.relay.save()

        local_time = datetime(2025, 1, 6, 10, 30, 0, tzinfo=dt_timezone(UTC.utcoffset(datetime.now(UTC))))
        with patch("odin.apps.relays.services.timezone.localtime", return_value=local_time):
            state, mode = self.relay.get_target_state()
            assert state == RelayState.ON
            assert mode == RelayMode.BASIC

    @pytest.mark.parametrize("periods", ("08:00-18:00", {"start_time": "08:00"}, (None,)))
    def test_relays__periodic_schedule_ignores_unusable_period_data(self, periods):
        """Test that context data that is not a list of period dicts falls back instead of raising."""
        self.relay.context = {"schedule": {"periods": periods}}
        self.relay.save()

        local_time = datetime(2025, 1, 6, 10, 30, 0, tzinfo=dt_timezone(UTC.utcoffset(datetime.now(UTC))))
        with patch("odin.apps.relays.services.timezone.localtime", return_value=local_time):
            state, mode = self.relay.get_target_state()
            assert state == RelayState.ON
            assert mode == RelayMode.FALLBACK

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
        """Test that a PUMP is off when outside temperature is 17°C or higher."""
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
        WeatherFactory(period=timezone.now(), data={"temp": {"avg": "12.0"}})

        local_time = datetime(2025, 1, 6, 8, 5, 0, tzinfo=dt_timezone(UTC.utcoffset(datetime.now(UTC))))
        with patch("odin.apps.relays.services.timezone.localtime", return_value=local_time):
            state, mode = relay.get_target_state()
            assert state == RelayState.ON
            assert mode == RelayMode.MIDSEASON

    def test_relays__pump_is_off_outside_every_second_hour_in_midseason(self):
        """Test that a PUMP is off during the idle hour and the second half of every 2-hour window."""
        relay: Relay = RelayFactory(type=RelayType.PUMP)  # noqa
        WeatherFactory(period=timezone.now(), data={"temp": {"avg": "12.0"}})

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
        """Test that a SERVO stays open (OFF) when outside temperature is 17°C or higher."""
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
        WeatherFactory(period=timezone.now(), data={"temp": {"avg": "12.0"}})

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
        WeatherFactory(period=timezone.now(), data={"temp": {"avg": "12.0"}})

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
        WeatherFactory(period=timezone.now(), data={"temp": {"avg": "12.0"}})

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
        WeatherFactory(period=timezone.now(), data={"temp": {"avg": "12.0"}})

        local_time = datetime(2025, 1, 6, hour, 30, 0, tzinfo=dt_timezone(UTC.utcoffset(datetime.now(UTC))))
        with patch("odin.apps.relays.services.timezone.localtime", return_value=local_time):
            state, mode = relay.get_target_state()
            assert state == expected_state
            assert mode == RelayMode.MIDSEASON

    @pytest.mark.parametrize("minute", (0, 10, 29))
    def test_relays__pump_midseason_active_window_spans_first_half_hour(self, minute):
        """Verify the pump midseason window runs for the first 30 minutes of the active hour."""
        relay: Relay = RelayFactory(type=RelayType.PUMP)  # noqa
        WeatherFactory(period=timezone.now(), data={"temp": {"avg": "12.0"}})

        local_time = datetime(2025, 1, 6, 8, minute, 0, tzinfo=dt_timezone(UTC.utcoffset(datetime.now(UTC))))
        with patch("odin.apps.relays.services.timezone.localtime", return_value=local_time):
            state, mode = relay.get_target_state()
            assert state == RelayState.ON
            assert mode == RelayMode.MIDSEASON

    @pytest.mark.parametrize("minute", (30, 45, 59))
    def test_relays__pump_midseason_is_off_in_second_half_hour(self, minute):
        """Verify the pump midseason window stops after the first 30 minutes of the active hour."""
        relay: Relay = RelayFactory(type=RelayType.PUMP)  # noqa
        WeatherFactory(period=timezone.now(), data={"temp": {"avg": "12.0"}})

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
        WeatherFactory(period=timezone.now(), data={"temp": {"avg": "12.0"}})

        local_time = datetime(2025, 1, 6, 8, minute, 0, tzinfo=dt_timezone(UTC.utcoffset(datetime.now(UTC))))
        with patch("odin.apps.relays.services.timezone.localtime", return_value=local_time):
            state, mode = relay.get_target_state()
            assert state == RelayState.OFF
            assert mode == RelayMode.MIDSEASON


@pytest.mark.django_db
class TestRelaysApparentTempGate:
    """MNT-253: above 17 °C the feels-like temperature extends midseason up to 20 °C.

    Below 17 °C the raw band stays authoritative, so wind can never pull a warm day out of
    summer or push a cold one into antifreeze.
    """

    @staticmethod
    def _at(hour: int, minute: int) -> datetime:
        return datetime(2025, 1, 6, hour, minute, 0, tzinfo=dt_timezone(UTC.utcoffset(datetime.now(UTC))))

    @staticmethod
    def _weather(temp: str, humidity: str | None = "85", wind_speed: str | None = "5") -> None:
        data: dict = {"temp": {"avg": temp}}
        if humidity is not None:
            data["humidity"] = humidity
        if wind_speed is not None:
            data["wind"] = {"speed": wind_speed}
        WeatherFactory(period=timezone.now(), data=data)

    @staticmethod
    def _pump() -> Relay:
        return RelayFactory(type=RelayType.PUMP)  # noqa

    @staticmethod
    def _servo() -> Relay:
        relay: Relay = RelayFactory(type=RelayType.SERVO)  # noqa
        sensor: Sensor = SensorFactory(relay=relay)  # noqa
        sensor.context = {"target_temp": "25.0", "hysteresis": "1.0"}
        sensor.save()
        SensorLogFactory(sensor=sensor, temp=Decimal("23.0"), created_at=timezone.now())
        return relay

    def test_relays__pump_enters_midseason_on_a_windy_warm_day(self):
        """18 °C at 85 % humidity and 5 m/s feels like 16.3 °C, so the pump keeps cycling."""
        relay = self._pump()
        self._weather(temp="18")

        with patch("odin.apps.relays.services.timezone.localtime", return_value=self._at(8, 5)):
            state, mode = relay.get_target_state()
            assert state == RelayState.ON
            assert mode == RelayMode.MIDSEASON

    def test_relays__pump_stays_in_summer_on_a_calm_warm_day(self):
        """The same 18 °C with a 1 m/s wind feels like 19.1 °C and stays summer."""
        relay = self._pump()
        self._weather(temp="18", wind_speed="1")

        with patch("odin.apps.relays.services.timezone.localtime", return_value=self._at(8, 5)):
            state, mode = relay.get_target_state()
            assert state == RelayState.OFF
            assert mode == RelayMode.SUMMER

    @pytest.mark.parametrize(("humidity", "wind_speed"), ((None, "5"), ("85", None), (None, None)))
    def test_relays__pump_falls_back_to_raw_temp_when_weather_is_incomplete(self, humidity, wind_speed):
        """A missing humidity or wind degenerates to the pre-MNT-253 raw-temp band."""
        relay = self._pump()
        self._weather(temp="18", humidity=humidity, wind_speed=wind_speed)

        with patch("odin.apps.relays.services.timezone.localtime", return_value=self._at(8, 5)):
            state, mode = relay.get_target_state()
            assert state == RelayState.OFF
            assert mode == RelayMode.SUMMER

    def test_relays__pump_ignores_feels_like_at_and_above_the_extended_edge(self):
        """20 °C with 21 m/s feels like 9 °C, but the extension is capped at 20 °C."""
        relay = self._pump()
        self._weather(temp="20", humidity="100", wind_speed="21")

        with patch("odin.apps.relays.services.timezone.localtime", return_value=self._at(8, 5)):
            state, mode = relay.get_target_state()
            assert state == RelayState.OFF
            assert mode == RelayMode.SUMMER

    def test_relays__pump_keeps_the_raw_lower_edge_in_midseason(self):
        """Wind may not lower the 10 °C edge: 10.0 °C falling to 2.4 °C feels-like is still not midseason."""
        relay = self._pump()
        self._weather(temp="10.0", wind_speed="10")

        with patch("odin.apps.relays.services.timezone.localtime", return_value=self._at(8, 5)):
            state, mode = relay.get_target_state()
            assert state == RelayState.ON
            assert mode == RelayMode.CYCLE

    def test_relays__pump_keeps_midseason_inside_the_raw_band_regardless_of_feels_like(self):
        """12 °C at 10 m/s feels like 4.9 °C, but the raw band still classifies it as midseason."""
        relay = self._pump()
        self._weather(temp="12", wind_speed="10")

        with patch("odin.apps.relays.services.timezone.localtime", return_value=self._at(8, 5)):
            state, mode = relay.get_target_state()
            assert state == RelayState.ON
            assert mode == RelayMode.MIDSEASON

    def test_relays__pump_antifreeze_stays_on_raw_temp(self):
        """-7.9 °C at 10 m/s feels like -18 °C, but antifreeze must not trigger above the raw -8 °C edge."""
        relay = self._pump()
        self._weather(temp="-7.9", wind_speed="10")

        with patch("odin.apps.relays.services.timezone.localtime", return_value=self._at(8, 5)):
            state, mode = relay.get_target_state()
            assert state == RelayState.ON
            assert mode == RelayMode.CYCLE

    def test_relays__servo_stays_open_in_extended_midseason(self):
        relay = self._servo()
        self._weather(temp="18")

        with patch("odin.apps.relays.services.timezone.localtime", return_value=self._at(8, 45)):
            state, mode = relay.get_target_state()
            assert state == RelayState.OFF
            assert mode == RelayMode.MIDSEASON

    def test_relays__servo_stays_open_in_summer_on_a_calm_warm_day(self):
        relay = self._servo()
        self._weather(temp="18", wind_speed="1")

        with patch("odin.apps.relays.services.timezone.localtime", return_value=self._at(8, 45)):
            state, mode = relay.get_target_state()
            assert state == RelayState.OFF
            assert mode == RelayMode.SUMMER


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
            # 23 °C sits below the 25 °C target minus the 1 °C hysteresis, so the circuit opens
            assert state == RelayState.OFF
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
            ("18.0", RelayMode.SUMMER),
            ("10.1", RelayMode.MIDSEASON),
            ("10.0", RelayMode.CYCLE),
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
        WeatherFactory(period=timezone.now(), data={"temp": {"avg": "12.0"}})

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
class TestRelaysOverrideSchedule:
    """MNT-255: an override schedule forces the relay state right after force_state."""

    @staticmethod
    def _at(hour: int, minute: int) -> datetime:
        return datetime(2025, 1, 6, hour, minute, 0, tzinfo=dt_timezone(UTC.utcoffset(datetime.now(UTC))))

    @classmethod
    def _pump(cls, override: list[dict], schedule: list[dict] | None = None) -> Relay:
        relay: Relay = RelayFactory(type=RelayType.PUMP)  # noqa
        relay.context = {"override_schedule": {"periods": override}}
        if schedule is not None:
            relay.context["schedule"] = {"periods": schedule}
        relay.save()
        return relay

    @classmethod
    def _servo(cls, override: list[dict], schedule: list[dict] | None = None) -> Relay:
        relay: Relay = RelayFactory(type=RelayType.SERVO)  # noqa
        sensor: Sensor = SensorFactory(relay=relay)  # noqa
        sensor.context = {"target_temp": "25.0", "hysteresis": "1.0"}
        sensor.save()
        SensorLogFactory(sensor=sensor, temp=Decimal("23.0"), created_at=timezone.now())
        relay.context = {"override_schedule": {"periods": override}}
        if schedule is not None:
            relay.context["schedule"] = {"periods": schedule}
        relay.save()
        return relay

    def test_relays__override_turns_pump_on_inside_the_period(self):
        relay = self._pump([{"start_time": "08:00", "end_time": "18:00", "target_state": "ON"}])

        with patch("odin.apps.relays.services.timezone.localtime", return_value=self._at(10, 30)):
            state, mode = relay.get_target_state()
            assert state == RelayState.ON
            assert mode == RelayMode.OVERRIDE

    def test_relays__override_turns_pump_off_inside_the_period(self):
        relay = self._pump([{"start_time": "08:00", "end_time": "18:00", "target_state": "OFF"}])

        with patch("odin.apps.relays.services.timezone.localtime", return_value=self._at(10, 30)):
            state, mode = relay.get_target_state()
            assert state == RelayState.OFF
            assert mode == RelayMode.OVERRIDE

    def test_relays__override_period_end_time_is_exclusive(self):
        """09:00 is not part of the 08:00-09:00 override, so the pump falls back to its default."""
        relay = self._pump([{"start_time": "08:00", "end_time": "09:00", "target_state": "OFF"}])

        with patch("odin.apps.relays.services.timezone.localtime", return_value=self._at(9, 0)):
            state, mode = relay.get_target_state()
            assert state == RelayState.ON
            assert mode == RelayMode.FALLBACK

    def test_relays__override_handles_overnight_periods(self):
        relay = self._pump([{"start_time": "22:00", "end_time": "06:00", "target_state": "ON"}])

        for hour, day in ((23, 6), (2, 7)):
            local_time = datetime(2025, 1, day, hour, 30, 0, tzinfo=dt_timezone(UTC.utcoffset(datetime.now(UTC))))
            with patch("odin.apps.relays.services.timezone.localtime", return_value=local_time):
                state, mode = relay.get_target_state()
                assert state == RelayState.ON
                assert mode == RelayMode.OVERRIDE

    def test_relays__force_state_still_wins_over_the_override(self):
        relay = self._pump([{"start_time": "00:00", "end_time": "23:59", "target_state": "ON"}])
        relay.force_state = RelayState.OFF
        relay.save()

        with patch("odin.apps.relays.services.timezone.localtime", return_value=self._at(10, 30)):
            state, mode = relay.get_target_state()
            assert state == RelayState.OFF
            assert mode == RelayMode.FORCED

    def test_relays__override_beats_summer_weather(self):
        relay = self._pump([{"start_time": "08:00", "end_time": "18:00", "target_state": "ON"}])
        WeatherFactory(period=timezone.now(), data={"temp": {"avg": "18"}, "humidity": "85", "wind": {"speed": "1"}})

        with patch("odin.apps.relays.services.timezone.localtime", return_value=self._at(10, 30)):
            state, mode = relay.get_target_state()
            assert state == RelayState.ON
            assert mode == RelayMode.OVERRIDE

    def test_relays__override_beats_the_cycle_window(self):
        relay = self._pump([{"start_time": "00:00", "end_time": "23:59", "target_state": "OFF"}])

        with patch("odin.apps.relays.services.timezone.localtime", return_value=self._at(8, 5)):
            state, mode = relay.get_target_state()
            assert state == RelayState.OFF
            assert mode == RelayMode.OVERRIDE

    def test_relays__override_beats_a_regular_schedule_period(self):
        relay = self._pump(
            [{"start_time": "00:00", "end_time": "23:59", "target_state": "OFF"}],
            schedule=[{"start_time": "00:00", "end_time": "23:59", "target_state": "ON"}],
        )

        with patch("odin.apps.relays.services.timezone.localtime", return_value=self._at(10, 30)):
            state, mode = relay.get_target_state()
            assert state == RelayState.OFF
            assert mode == RelayMode.OVERRIDE

    def test_relays__schedule_applies_outside_the_override_window(self):
        relay = self._pump(
            [{"start_time": "08:00", "end_time": "09:00", "target_state": "OFF"}],
            schedule=[{"start_time": "00:00", "end_time": "23:59", "target_state": "ON"}],
        )

        with patch("odin.apps.relays.services.timezone.localtime", return_value=self._at(10, 30)):
            state, mode = relay.get_target_state()
            assert state == RelayState.ON
            assert mode == RelayMode.BASIC

    def test_relays__servo_override_opens_the_circuit_for_an_on_window(self):
        """A servo's ON closes the circuit, so an ON heating window must yield the physical OFF."""
        relay = self._servo([{"start_time": "08:00", "end_time": "18:00", "target_state": "ON"}])

        with patch("odin.apps.relays.services.timezone.localtime", return_value=self._at(10, 30)):
            state, mode = relay.get_target_state()
            assert state == RelayState.OFF
            assert mode == RelayMode.OVERRIDE

    def test_relays__servo_override_closes_the_circuit_for_an_off_window(self):
        relay = self._servo([{"start_time": "08:00", "end_time": "18:00", "target_state": "OFF"}])

        with patch("odin.apps.relays.services.timezone.localtime", return_value=self._at(10, 30)):
            state, mode = relay.get_target_state()
            assert state == RelayState.ON
            assert mode == RelayMode.OVERRIDE

    def test_relays__valve_follows_the_override(self):
        relay: Relay = RelayFactory(type=RelayType.VALVE)  # noqa
        relay.context = {
            "override_schedule": {"periods": [{"start_time": "08:00", "end_time": "18:00", "target_state": "OFF"}]}
        }
        relay.save()

        with patch("odin.apps.relays.services.timezone.localtime", return_value=self._at(10, 30)):
            state, mode = relay.get_target_state()
            assert state == RelayState.OFF
            assert mode == RelayMode.OVERRIDE

    @pytest.mark.parametrize(
        "period",
        (
            {"start_time": "00:00", "end_time": "23:59"},
            {"start_time": "00:00", "end_time": "23:59", "target_state": None},
            {"start_time": "00:00", "end_time": "23:59", "target_state": "BLAH"},
        ),
    )
    def test_relays__override_period_without_a_valid_target_state_is_skipped(self, period):
        relay = self._pump(
            [period],
            schedule=[{"start_time": "00:00", "end_time": "23:59", "target_state": "ON"}],
        )

        with patch("odin.apps.relays.services.timezone.localtime", return_value=self._at(10, 30)):
            state, mode = relay.get_target_state()
            assert state == RelayState.ON
            assert mode == RelayMode.BASIC

    def test_relays__override_uses_the_matching_period_of_two(self):
        relay = self._pump(
            [
                {"start_time": "00:00", "end_time": "08:00", "target_state": "OFF"},
                {"start_time": "08:00", "end_time": "20:00", "target_state": "ON"},
            ]
        )

        with patch("odin.apps.relays.services.timezone.localtime", return_value=self._at(10, 30)):
            state, mode = relay.get_target_state()
            assert state == RelayState.ON
            assert mode == RelayMode.OVERRIDE

    def test_relays__override_skips_malformed_periods(self):
        """A hand-edited period with an unusable time is skipped, the next one still applies."""
        relay = self._pump(
            [
                {"start_time": None, "end_time": "18:00", "target_state": "ON"},
                {"start_time": "08:00", "end_time": "18:00", "target_state": "OFF"},
            ]
        )

        with patch("odin.apps.relays.services.timezone.localtime", return_value=self._at(10, 30)):
            state, mode = relay.get_target_state()
            assert state == RelayState.OFF
            assert mode == RelayMode.OVERRIDE

    def test_relays__override_ignores_unusable_context_data(self):
        """A context that is not a period list must not break the read path."""
        relay = self._pump([])
        relay.context = {"override_schedule": "08:00-18:00"}
        relay.save()

        with patch("odin.apps.relays.services.timezone.localtime", return_value=self._at(10, 30)):
            state, mode = relay.get_target_state()
            assert state == RelayState.ON
            assert mode == RelayMode.FALLBACK


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
