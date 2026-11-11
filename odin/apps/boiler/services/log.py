"""Store periodic snapshots of the boiler's mode and setpoints."""

import logging

from odin.apps.boiler.models import BoilerLog
from odin.apps.boiler.services.state import BoilerState, get_current_state


logger = logging.getLogger(__name__)


class BoilerLogService:
    """Persist the boiler's current state as ``BoilerLog`` rows."""

    def get_state(self) -> BoilerState:
        """The state to store: the mode in effect and the active setpoints."""
        return get_current_state()

    def log(self) -> BoilerLog:
        """Store one snapshot row for the current state and return it."""
        state = self.get_state()
        entry = BoilerLog.objects.create(hcmode=state.mode, flow_temp=state.flow_temp, hwc_temp=state.hwc_temp)
        logger.info(f"Boiler state logged: {entry}")
        return entry


def log_boiler_status() -> BoilerLog:
    """Scheduler entry point: store one snapshot of the current boiler state."""
    return BoilerLogService().log()
