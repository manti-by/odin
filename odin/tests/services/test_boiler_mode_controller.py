import pytest

from django.utils import timezone

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


@pytest.fixture
def boiler_state(settings, tmp_path):
    settings.BOILER_STATE_FILE = str(tmp_path / "state")
    settings.BOILER_LOCK_FILE = str(tmp_path / "state.lock")
    return tmp_path / "state"


@pytest.mark.django_db
class TestGetCurrentMode:
    @pytest.mark.parametrize(
        ("override", "expected"),
        [
            ("water;0;55;-;0;0;0;0;0;0", BoilerMode.BOILING),
            ("heat;45;-;0;0;0;0;0;0;0", BoilerMode.HEATING),
            ("auto;45;55;-;0;0;0;0;0;0", BoilerMode.MIXED),
            ("off;0;0;-;0;0;0;0;0;0", BoilerMode.OFF),
        ],
    )
    def test__override_wins(self, boiler_state, override, expected):
        boiler_state.write_text(f"{override}\n")

        assert BoilerModeService().get_current_mode() == expected

    def test__no_override_falls_back_to_target(self, boiler_state):
        create_weather("20.0")

        assert BoilerModeService().get_current_mode() == BoilerMode.HEATING

    def test__no_override_no_weather__mixed(self, boiler_state):
        assert BoilerModeService().get_current_mode() == BoilerMode.MIXED
