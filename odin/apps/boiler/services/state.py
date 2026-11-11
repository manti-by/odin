"""The boiler state as the status API reports it: the mode in effect plus the active setpoints."""

from dataclasses import dataclass

from odin.apps.boiler.models import BoilerMode
from odin.apps.boiler.services.mode import BoilerModeService
from odin.apps.boiler.services.status import BoilerStatusService, parse_override


@dataclass(frozen=True)
class BoilerState:
    """Boiler mode plus the setpoints saved in the active override."""

    mode: BoilerMode
    flow_temp: int | None
    hwc_temp: int | None


def get_current_state() -> BoilerState:
    """Read the boiler state the way ``BoilerStatusView`` reads it.

    The mode is the one in effect (the active override wins, otherwise the mode decided from the
    weather and the pumps); the setpoints come from the saved override file, so both stay ``None``
    while the boiler runs on its panel settings.
    """
    override = BoilerStatusService().current_override()
    flow_temp = hwc_temp = None
    if override:
        _, flow_temp, hwc_temp = parse_override(override)

    return BoilerState(mode=BoilerModeService().get_current_mode(), flow_temp=flow_temp, hwc_temp=hwc_temp)
