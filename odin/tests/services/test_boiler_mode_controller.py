from unittest.mock import MagicMock, patch

import pytest

from django.utils import timezone

from odin.apps.boiler.services.controller import (
    DEFAULT_HEATING_FLOW_TEMP,
    DEFAULT_HWC_TEMP,
    BoilerModeController,
    run_boiler_mode_controller,
)
from odin.apps.boiler.services.mode import BoilerMode, BoilerModeService
from odin.apps.relays.models import RelayState, RelayType
from odin.tests.factories import RelayFactory, WeatherFactory


def create_weather(temp: str) -> None:
    WeatherFactory(period=timezone.now(), data={"temp": {"avg": temp}})


def create_pumps(*states: RelayState) -> None:
    for state in states:
        RelayFactory(type=RelayType.PUMP, force_state=state)


@pytest.mark.django_db
class TestGetPumpsState:
    def test__no_active_pumps__unknown(self):
        assert BoilerModeService().get_pumps_state() == RelayState.UNKNOWN

    def test__inactive_pumps_ignored(self):
        RelayFactory(type=RelayType.PUMP, force_state=RelayState.ON, is_active=False)

        assert BoilerModeService().get_pumps_state() == RelayState.UNKNOWN

    def test__all_pumps_off__off(self):
        create_pumps(RelayState.OFF, RelayState.OFF)

        assert BoilerModeService().get_pumps_state() == RelayState.OFF

    def test__any_pump_on__on(self):
        create_pumps(RelayState.OFF, RelayState.ON)

        assert BoilerModeService().get_pumps_state() == RelayState.ON


@pytest.mark.django_db
class TestGetTargetMode:
    def test__summer__heating(self):
        create_pumps(RelayState.ON)
        create_weather("20.0")

        assert BoilerModeService().get_target_mode() == BoilerMode.HEATING

    def test__summer_at_threshold__heating(self):
        create_pumps(RelayState.ON)
        create_weather("15.0")

        assert BoilerModeService().get_target_mode() == BoilerMode.HEATING

    def test__winter_with_demand__mixed(self):
        create_pumps(RelayState.ON)
        create_weather("0.0")

        assert BoilerModeService().get_target_mode() == BoilerMode.MIXED

    def test__winter_pumps_off__heating(self):
        create_pumps(RelayState.OFF)
        create_weather("0.0")

        assert BoilerModeService().get_target_mode() == BoilerMode.HEATING

    def test__any_pump_on_aggregates_to_on(self):
        create_pumps(RelayState.OFF, RelayState.ON)
        create_weather("0.0")

        assert BoilerModeService().get_target_mode() == BoilerMode.MIXED

    def test__no_weather__mixed(self):
        create_pumps(RelayState.ON)

        assert BoilerModeService().get_target_mode() == BoilerMode.MIXED

    def test__no_pumps__mixed(self):
        create_weather("0.0")

        assert BoilerModeService().get_target_mode() == BoilerMode.MIXED

    def test__boil_override_active__none(self, settings, tmp_path):
        settings.BOILER_STATE_FILE = str(tmp_path / "state")
        settings.BOILER_LOCK_FILE = str(tmp_path / "state.lock")
        (tmp_path / "state").write_text("water;0;55;-;0;0;0;0;0;0\n")
        create_pumps(RelayState.ON)
        create_weather("0.0")

        assert BoilerModeService().get_target_mode() is None

    def test__construction__no_weather_query(self, django_assert_num_queries):
        with django_assert_num_queries(0):
            BoilerModeService()


class TestBoilerModeController:
    @pytest.fixture
    def mode_service(self):
        return MagicMock(spec=BoilerModeService)

    @pytest.fixture
    def boiler_service(self):
        return MagicMock()

    def test__boil_override_active__no_set_call(self, mode_service, boiler_service):
        mode_service.get_target_mode.return_value = None

        result = BoilerModeController(mode_service, boiler_service).run()

        assert result is None
        boiler_service.set_heating.assert_not_called()
        boiler_service.set_mixed.assert_not_called()
        boiler_service.set_off.assert_not_called()
        boiler_service.clear_override.assert_not_called()

    def test__heating__set_heating(self, mode_service, boiler_service):
        mode_service.get_target_mode.return_value = BoilerMode.HEATING
        boiler_service.set_heating.return_value = "heat"

        result = BoilerModeController(mode_service, boiler_service).run()

        assert result == "heat"
        boiler_service.set_heating.assert_called_once_with(DEFAULT_HEATING_FLOW_TEMP)

    def test__mixed__set_mixed(self, mode_service, boiler_service):
        mode_service.get_target_mode.return_value = BoilerMode.MIXED
        boiler_service.set_mixed.return_value = "auto"

        result = BoilerModeController(mode_service, boiler_service).run()

        assert result == "auto"
        boiler_service.set_mixed.assert_called_once_with(DEFAULT_HEATING_FLOW_TEMP, DEFAULT_HWC_TEMP)

    def test__off__set_off(self, mode_service, boiler_service):
        mode_service.get_target_mode.return_value = BoilerMode.OFF
        boiler_service.set_off.return_value = "off"

        result = BoilerModeController(mode_service, boiler_service).run()

        assert result == "off"
        boiler_service.set_off.assert_called_once_with()

    def test__clear_override__clear_override(self, mode_service, boiler_service):
        mode_service.get_target_mode.return_value = BoilerMode.CLEAR_OVERRIDE

        result = BoilerModeController(mode_service, boiler_service).run()

        assert result is None
        boiler_service.clear_override.assert_called_once_with()

    def test__unknown_mode__raises(self, mode_service, boiler_service):
        mode_service.get_target_mode.return_value = "bogus"

        with pytest.raises(ValueError, match="Unsupported boiler mode"):
            BoilerModeController(mode_service, boiler_service).run()


class TestRunBoilerModeController:
    @patch("odin.apps.boiler.services.controller.BoilerModeController")
    def test__wrapper_delegates_to_controller(self, mock_controller):
        mock_controller.return_value.run.return_value = "auto"

        assert run_boiler_mode_controller() == "auto"
        mock_controller.return_value.run.assert_called_once_with()


@pytest.mark.django_db
class TestSchedulerWiring:
    def test__boiler_mode_job_registered(self):
        from odin.apps.core import scheduler as scheduler_module

        job = scheduler_module.scheduler.get_job("update_boiler_mode")

        assert job is not None
        assert job.max_instances == 1

    @patch("odin.apps.boiler.services.controller.run_boiler_mode_controller")
    def test__controller_error_does_not_propagate(self, mock_run):
        from odin.apps.core.scheduler import schedule_update_boiler_mode

        mock_run.side_effect = RuntimeError("ebusd is down")

        schedule_update_boiler_mode()

        mock_run.assert_called_once_with()
