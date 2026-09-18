from __future__ import annotations

import logging

from odin.apps.boiler.services.mode import BoilerMode, BoilerModeService
from odin.apps.boiler.services.status import BoilerStatusService


logger = logging.getLogger(__name__)

DEFAULT_HEATING_FLOW_TEMP = 55
DEFAULT_HWC_TEMP = 45


class BoilerModeController:
    """Apply the boiler mode decided by :class:`BoilerModeService`.

    The MNT-206 split leaves applying the mode to the caller: this controller is
    the "apply" half that translates a :class:`BoilerMode` into a
    :class:`BoilerStatusService` SetMode write. Every write goes through the
    ``BOILER_LOCK_FILE`` flock held by ``BoilerStatusService``, so it is safe to
    run from a periodic scheduler tick next to ``boiler-refresh.timer`` and the
    manual ``boiler-set`` command.
    """

    def __init__(
        self,
        mode_service: BoilerModeService | None = None,
        boiler_service: BoilerStatusService | None = None,
    ) -> None:
        """Wire the decision service and the SetMode writer."""
        self.mode_service = mode_service or BoilerModeService()
        self.boiler_service = boiler_service or BoilerStatusService()

    def run(self) -> str | None:
        """Apply the decided mode, returning the written values or None when skipped."""
        mode = self.mode_service.get_target_mode()
        if mode is None:
            logger.info("No boiler mode decided, leaving the boiler mode untouched")
            return None

        logger.info(f"Boiler mode decided: {mode}")
        return self.apply(mode)

    def apply(self, mode: BoilerMode) -> str | None:
        """Write the decided mode, rechecking the water override under the lock; None when skipped."""
        match mode:
            case BoilerMode.HEATING:
                return self.boiler_service.apply_automatic("heat", DEFAULT_HEATING_FLOW_TEMP, None)
            case BoilerMode.MIXED:
                return self.boiler_service.apply_automatic("auto", DEFAULT_HEATING_FLOW_TEMP, DEFAULT_HWC_TEMP)
            case BoilerMode.OFF:
                return self.boiler_service.apply_automatic("off", 0, 0)
            case BoilerMode.CLEAR_OVERRIDE:
                self.boiler_service.clear_automatic()
                return None
            case _:
                raise ValueError(f"Unsupported boiler mode: {mode}")


def run_boiler_mode_controller() -> str | None:
    """Thin scheduler entry point: decide and apply the boiler mode once."""
    return BoilerModeController().run()
