from datetime import datetime
from decimal import Decimal
from unittest.mock import MagicMock, patch
from zoneinfo import ZoneInfo

import pytest

from django.utils import timezone

from odin.apps.boiler.services import (
    DEFAULT_HEATING_FLOW_TEMP,
    DEFAULT_HWC_TEMP,
    BoilerModeController,
    BoilerService,
)
from odin.apps.relays.models import Relay, RelayState, RelayType
from odin.tests.factories import RelayFactory, SensorFactory, SensorLogFactory, WeatherFactory


@pytest.fixture
def boiler_service(settings, tmp_path):
    settings.BOILER_STATE_FILE = str(tmp_path / "state")
    settings.BOILER_LOCK_FILE = str(tmp_path / "state.lock")
    return BoilerService(client=MagicMock())


@pytest.fixture
def relay_target_state():
    with patch("odin.apps.boiler.services.RelayTargetStateService") as mock:
        yield mock


def configure_target_states(mock, pump_state: RelayState, servo_state: RelayState) -> None:
    def factory(relay):
        instance = MagicMock()
        instance.get_target_state.return_value = pump_state if relay.type == RelayType.PUMP else servo_state
        return instance

    mock.side_effect = factory


def create_weather(temp: str) -> None:
    WeatherFactory(period=timezone.now(), data={"temp": {"avg": temp}})


@pytest.mark.django_db
class TestBoilerModeController:
    def test_run__summer_turns_both_circuits_off(self, boiler_service, relay_target_state):
        RelayFactory(type=RelayType.PUMP)
        RelayFactory(type=RelayType.SERVO)
        create_weather("20.0")
        configure_target_states(relay_target_state, RelayState.ON, RelayState.ON)

        with patch.object(boiler_service, "set_off", return_value="off") as mock_set_off:
            controller = BoilerModeController(boiler_service=boiler_service)
            assert controller.run() == "off"

        mock_set_off.assert_called_once_with()

    def test_run__summer_at_threshold_turns_both_circuits_off(self, boiler_service, relay_target_state):
        RelayFactory(type=RelayType.PUMP)
        RelayFactory(type=RelayType.SERVO)
        create_weather("15.0")
        configure_target_states(relay_target_state, RelayState.ON, RelayState.ON)

        with patch.object(boiler_service, "set_off", return_value="off") as mock_set_off:
            BoilerModeController(boiler_service=boiler_service).run()

        mock_set_off.assert_called_once_with()

    def test_run__antifreeze_heats_the_system(self, boiler_service, relay_target_state):
        RelayFactory(type=RelayType.PUMP)
        RelayFactory(type=RelayType.SERVO)
        create_weather("-9.0")
        configure_target_states(relay_target_state, RelayState.ON, RelayState.OFF)

        with patch.object(boiler_service, "set_heating", return_value="heat") as mock_set_heating:
            assert BoilerModeController(boiler_service=boiler_service).run() == "heat"

        mock_set_heating.assert_called_once_with(DEFAULT_HEATING_FLOW_TEMP)

    def test_run__antifreeze_at_threshold_uses_winter_band(self, boiler_service, relay_target_state):
        RelayFactory(type=RelayType.PUMP)
        RelayFactory(type=RelayType.SERVO)
        create_weather("-8.0")
        configure_target_states(relay_target_state, RelayState.ON, RelayState.ON)

        with patch.object(boiler_service, "set_mixed", return_value="mixed") as mock_set_mixed:
            BoilerModeController(boiler_service=boiler_service).run()

        mock_set_mixed.assert_called_once_with(DEFAULT_HEATING_FLOW_TEMP, DEFAULT_HWC_TEMP)

    def test_run__winter_with_demand_sets_mixed(self, boiler_service, relay_target_state):
        RelayFactory(type=RelayType.PUMP)
        RelayFactory(type=RelayType.SERVO)
        create_weather("0.0")
        configure_target_states(relay_target_state, RelayState.ON, RelayState.ON)

        with patch.object(boiler_service, "set_mixed", return_value="mixed") as mock_set_mixed:
            assert BoilerModeController(boiler_service=boiler_service).run() == "mixed"

        mock_set_mixed.assert_called_once_with(DEFAULT_HEATING_FLOW_TEMP, DEFAULT_HWC_TEMP)

    def test_run__just_below_midseason_sets_mixed(self, boiler_service, relay_target_state):
        RelayFactory(type=RelayType.PUMP)
        RelayFactory(type=RelayType.SERVO)
        create_weather("7.9")
        configure_target_states(relay_target_state, RelayState.ON, RelayState.ON)

        with patch.object(boiler_service, "set_mixed", return_value="mixed") as mock_set_mixed:
            BoilerModeController(boiler_service=boiler_service).run()

        mock_set_mixed.assert_called_once_with(DEFAULT_HEATING_FLOW_TEMP, DEFAULT_HWC_TEMP)

    def test_run__midseason_at_threshold_sets_heating(self, boiler_service, relay_target_state):
        RelayFactory(type=RelayType.PUMP)
        RelayFactory(type=RelayType.SERVO)
        create_weather("8.0")
        configure_target_states(relay_target_state, RelayState.ON, RelayState.ON)

        with patch.object(boiler_service, "set_heating", return_value="heat") as mock_set_heating:
            BoilerModeController(boiler_service=boiler_service).run()

        mock_set_heating.assert_called_once_with(DEFAULT_HEATING_FLOW_TEMP)

    def test_run__midseason_with_demand_sets_heating(self, boiler_service, relay_target_state):
        RelayFactory(type=RelayType.PUMP)
        RelayFactory(type=RelayType.SERVO)
        create_weather("12.0")
        configure_target_states(relay_target_state, RelayState.ON, RelayState.ON)

        with patch.object(boiler_service, "set_heating", return_value="heat") as mock_set_heating:
            assert BoilerModeController(boiler_service=boiler_service).run() == "heat"

        mock_set_heating.assert_called_once_with(DEFAULT_HEATING_FLOW_TEMP)

    def test_run__no_demand_turns_both_circuits_off(self, boiler_service, relay_target_state):
        RelayFactory(type=RelayType.PUMP)
        RelayFactory(type=RelayType.SERVO)
        create_weather("0.0")
        configure_target_states(relay_target_state, RelayState.OFF, RelayState.OFF)

        with patch.object(boiler_service, "set_off", return_value="off") as mock_set_off:
            assert BoilerModeController(boiler_service=boiler_service).run() == "off"

        mock_set_off.assert_called_once_with()

    def test_run__pump_only_winter_turns_both_circuits_off(self, boiler_service, relay_target_state):
        RelayFactory(type=RelayType.PUMP)
        RelayFactory(type=RelayType.SERVO)
        create_weather("0.0")
        configure_target_states(relay_target_state, RelayState.ON, RelayState.OFF)

        with patch.object(boiler_service, "set_off", return_value="off") as mock_set_off:
            BoilerModeController(boiler_service=boiler_service).run()

        mock_set_off.assert_called_once_with()

    def test_run__any_pump_on_aggregates_to_on(self, boiler_service, relay_target_state):
        pump_off: Relay = RelayFactory(type=RelayType.PUMP)
        RelayFactory(type=RelayType.PUMP)
        RelayFactory(type=RelayType.SERVO)

        def factory(relay):
            instance = MagicMock()
            if relay.type == RelayType.PUMP:
                instance.get_target_state.return_value = RelayState.OFF if relay.pk == pump_off.pk else RelayState.ON
            else:
                instance.get_target_state.return_value = RelayState.ON
            return instance

        relay_target_state.side_effect = factory
        create_weather("0.0")

        with patch.object(boiler_service, "set_mixed", return_value="mixed") as mock_set_mixed:
            BoilerModeController(boiler_service=boiler_service).run()

        mock_set_mixed.assert_called_once_with(DEFAULT_HEATING_FLOW_TEMP, DEFAULT_HWC_TEMP)

    def test_run__unknown_relay_state_clears_override(self, boiler_service, relay_target_state):
        RelayFactory(type=RelayType.PUMP)
        RelayFactory(type=RelayType.SERVO)
        create_weather("0.0")
        configure_target_states(relay_target_state, RelayState.UNKNOWN, RelayState.OFF)

        with patch.object(boiler_service, "clear_override") as mock_clear_override:
            assert BoilerModeController(boiler_service=boiler_service).run() is None

        mock_clear_override.assert_called_once_with()

    def test_run__no_relays_clears_override(self, boiler_service, relay_target_state):
        create_weather("0.0")

        with patch.object(boiler_service, "clear_override") as mock_clear_override:
            assert BoilerModeController(boiler_service=boiler_service).run() is None

        mock_clear_override.assert_called_once_with()

    def test_run__skips_when_boiling_override_active(self, boiler_service, relay_target_state):
        RelayFactory(type=RelayType.PUMP)
        RelayFactory(type=RelayType.SERVO)
        create_weather("0.0")
        configure_target_states(relay_target_state, RelayState.ON, RelayState.ON)

        with (
            patch.object(boiler_service, "current_override", return_value="water;0;55;-;0;0;0;0;0;0"),
            patch.object(boiler_service, "set_heating") as mock_set_heating,
            patch.object(boiler_service, "set_mixed") as mock_set_mixed,
            patch.object(boiler_service, "set_off") as mock_set_off,
            patch.object(boiler_service, "clear_override") as mock_clear_override,
        ):
            assert BoilerModeController(boiler_service=boiler_service).run() is None

        mock_set_heating.assert_not_called()
        mock_set_mixed.assert_not_called()
        mock_set_off.assert_not_called()
        mock_clear_override.assert_not_called()

    def test_run__skips_when_weather_missing(self, boiler_service, relay_target_state):
        RelayFactory(type=RelayType.PUMP)
        RelayFactory(type=RelayType.SERVO)
        configure_target_states(relay_target_state, RelayState.ON, RelayState.ON)

        with patch.object(boiler_service, "set_heating") as mock_set_heating:
            assert BoilerModeController(boiler_service=boiler_service).run() is None

        mock_set_heating.assert_not_called()

    def test_run__writes_mode_to_ebusd_client(self, boiler_service, relay_target_state):
        RelayFactory(type=RelayType.PUMP)
        RelayFactory(type=RelayType.SERVO)
        create_weather("12.0")
        configure_target_states(relay_target_state, RelayState.ON, RelayState.ON)

        controller = BoilerModeController(boiler_service=boiler_service)
        controller.run()

        boiler_service.client.command.assert_called_once()
        assert boiler_service.client.command.call_args.args[0].startswith("write -def")
        assert boiler_service.current_override() is not None

    @patch("odin.apps.relays.services.timezone.localtime")
    def test_run__handles_dst_transition_with_real_target_state_service(self, mock_localtime, boiler_service):
        mock_localtime.return_value = timezone.make_aware(datetime(2026, 3, 29, 3, 30), ZoneInfo("Europe/Berlin"))

        pump: Relay = RelayFactory(type=RelayType.PUMP, force_state=RelayState.ON)
        servo = RelayFactory(type=RelayType.SERVO, force_state=RelayState.ON)
        sensor = SensorFactory(relay_id=servo.relay_id)
        SensorLogFactory(sensor_id=sensor.sensor_id, temp=Decimal("20.0"), created_at=timezone.now())
        create_weather("0.0")

        with patch.object(boiler_service, "set_mixed", return_value="mixed") as mock_set_mixed:
            assert BoilerModeController(boiler_service=boiler_service).run() == "mixed"

        mock_set_mixed.assert_called_once_with(DEFAULT_HEATING_FLOW_TEMP, DEFAULT_HWC_TEMP)
        assert pump.target_state == RelayState.ON
