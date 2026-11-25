"""Store periodic snapshots of the boiler's mode and setpoints."""

import logging

from odin.apps.boiler.models import BoilerLog
from odin.apps.boiler.services.state import BoilerState, get_current_state
from odin.apps.boiler.services.status import BoilerStatusService, parse_temp


logger = logging.getLogger(__name__)


class BoilerLogService:
    """Persist the boiler's current state as ``BoilerLog`` rows."""

    def __init__(self, status: BoilerStatusService | None = None):
        self.status = status or BoilerStatusService()

    def get_state(self, status: dict[str, str] | None = None) -> BoilerState:
        """The mode in effect plus the active setpoints, falling back to live eBus setpoints."""
        status = self.status.status() if status is None else status
        state = get_current_state()
        return BoilerState(
            mode=state.mode,
            flow_temp=state.flow_temp if state.flow_temp is not None else parse_temp(status.get("FlowTempDesired", "")),
            hwc_temp=state.hwc_temp if state.hwc_temp is not None else parse_temp(status.get("StorageTempDesired", "")),
        )

    def log(self) -> BoilerLog:
        """Store one snapshot row for the current state and return it."""
        status = self.status.status()
        state = self.get_state(status)
        entry = BoilerLog.objects.create(
            hcmode=state.mode,
            flow_temp=state.flow_temp,
            hwc_temp=state.hwc_temp,
            context=status,
        )
        logger.info(f"Boiler state logged: {entry}")
        return entry


def log_boiler_status() -> BoilerLog:
    """Scheduler entry point: store one snapshot of the current boiler state."""
    return BoilerLogService().log()
