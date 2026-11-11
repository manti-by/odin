import pytest

from odin.apps.boiler.models import BoilerLog, BoilerMode
from odin.apps.boiler.services.log import BoilerLogService, log_boiler_status
from odin.apps.core import scheduler
from odin.tests.factories import create_weather


@pytest.mark.django_db
class TestBoilerLogService:
    def test__heating_override__mode_and_flow_temp(self, boiler_state):
        boiler_state.write_text("heat;45;-;0;0;0;0;0;0;0\n")

        entry = BoilerLogService().log()

        assert entry.hcmode == BoilerMode.HEATING
        assert entry.flow_temp == 45
        assert entry.hwc_temp is None
        assert entry.created_at is not None
        assert BoilerLog.objects.count() == 1

    def test__boiling_override__both_setpoints(self, boiler_state):
        boiler_state.write_text("water;0;55;-;0;0;0;0;0;0\n")

        entry = BoilerLogService().log()

        assert entry.hcmode == BoilerMode.BOILING
        assert entry.flow_temp == 0
        assert entry.hwc_temp == 55

    def test__mixed_override__both_setpoints(self, boiler_state):
        boiler_state.write_text("auto;45;55;-;0;0;0;0;0;0\n")

        entry = BoilerLogService().log()

        assert entry.hcmode == BoilerMode.MIXED
        assert entry.flow_temp == 45
        assert entry.hwc_temp == 55

    def test__no_override__panel_mode_leaves_setpoints_empty(self, boiler_state):
        create_weather("20.0")

        entry = BoilerLogService().log()

        assert entry.hcmode == BoilerMode.HEATING
        assert entry.flow_temp is None
        assert entry.hwc_temp is None

    def test__no_override_no_weather__mixed(self, boiler_state):
        entry = BoilerLogService().log()

        assert entry.hcmode == BoilerMode.MIXED

    def test__entry_point__creates_a_row(self, boiler_state):
        entry = log_boiler_status()

        assert BoilerLog.objects.filter(pk=entry.pk).exists()


class TestLogBoilerStatusSchedule:
    def test__enqueues_the_callable(self, monkeypatch):
        enqueued = []
        monkeypatch.setattr(scheduler.queue, "enqueue", lambda func, *args, **kwargs: enqueued.append(func))

        scheduler.schedule_log_boiler_status()

        assert enqueued == [log_boiler_status]
