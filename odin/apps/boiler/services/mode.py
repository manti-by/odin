from __future__ import annotations

import logging

from django.db import models

from odin.apps.boiler.services.status import BoilerStatusService
from odin.apps.relays.models import Relay, RelayState, RelayType
from odin.apps.relays.services import RelayTargetStateService
from odin.apps.weather.models import Weather


logger = logging.getLogger(__name__)


class BoilerMode(models.TextChoices):
    HEATING = "heating", "Heating"
    MIXED = "mixed", "Mixed"
    OFF = "off", "Off"
    BOILING = "boiling", "Boiling"
    CLEAR_OVERRIDE = "clear_override", "Clear override"


# The override's first token is the commanded hcmode; it maps 1:1 onto a display mode.
OVERRIDE_MODES = {
    "auto": BoilerMode.MIXED,
    "heat": BoilerMode.HEATING,
    "water": BoilerMode.BOILING,
    "off": BoilerMode.OFF,
}


class BoilerModeService:
    def get_pumps_state(self) -> RelayState:
        """Aggregate active pump relays to a single state."""
        states = [
            RelayTargetStateService(relay).get_target_state()[0]
            for relay in Relay.objects.active().filter(type=RelayType.PUMP)
        ]
        if not states:
            return RelayState.UNKNOWN

        if all(state == RelayState.OFF for state in states):
            return RelayState.OFF

        return RelayState.ON

    def get_target_mode(self) -> BoilerMode | None:
        """Decide the boiler mode, or None to leave a water override untouched.

        The water check here is a best-effort fast path; the atomic guarantee lives in
        ``BoilerStatusService.apply_automatic``/``clear_automatic``, which recheck under the lock.
        """
        boiler_override = BoilerStatusService().current_override()
        if boiler_override and boiler_override.split(";", 1)[0] == "water":
            logger.info("Boiling override active, leaving the boiler mode untouched")
            return None

        weather = Weather.objects.current()
        if not weather or (outside_temp := weather.temp) is None:
            return BoilerMode.MIXED

        if outside_temp >= 15:
            return BoilerMode.HEATING

        if self.get_pumps_state() == RelayState.OFF:
            return BoilerMode.HEATING

        return BoilerMode.MIXED

    def get_current_mode(self) -> BoilerMode:
        """Mode actually in effect for display: the active override wins, otherwise the target mode."""
        boiler_override = BoilerStatusService().current_override()
        if boiler_override:
            hcmode = boiler_override.split(";", 1)[0]
            if mode := OVERRIDE_MODES.get(hcmode):
                return mode

        return self.get_target_mode() or BoilerMode.MIXED
