import pytest

from django.core.management import call_command

from odin.apps.boiler.models import BoilerLog, BoilerMode


@pytest.mark.django_db
class TestBoilerLogCommand:
    def test__creates_a_row(self, boiler_state):
        boiler_state.write_text("water;0;55;-;0;0;0;0;0;0\n")

        call_command("boiler_log")

        entry = BoilerLog.objects.get()
        assert entry.hcmode == BoilerMode.BOILING
        assert entry.hwc_temp == 55

    def test__prints_the_stored_row(self, boiler_state, capsys):
        call_command("boiler_log")

        assert "BoilerLog" in capsys.readouterr().out
