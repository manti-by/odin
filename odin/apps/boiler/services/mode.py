from __future__ import annotations

from django.db import models

from odin.apps.boiler.services.status import BoilerStatusService
from odin.apps.relays.models import Relay, RelayState, RelayType
from odin.apps.relays.services import RelayTargetStateService
from odin.apps.weather.models import Weather


class BoilerMode(models.TextChoices):
    HEATING = "heating", "Heating"
    MIXED = "mixed", "Mixed"
    OFF = "off", "Off"
    CLEAR_OVERRIDE = "clear_override", "Clear override"


class BoilerModeService:
    def __init__(self):
        self.weather = Weather.objects.current()

    def get_pumps_state(self) -> RelayState:
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
        boiler_override = BoilerStatusService().current_override()
        if boiler_override and boiler_override.split(";", 1)[0] == "water":
            return None

        if not self.weather or (outside_temp := self.weather.temp) is None:
            return BoilerMode.MIXED

        if outside_temp >= 15:
            return BoilerMode.HEATING

        if self.get_pumps_state() == RelayState.OFF:
            return BoilerMode.HEATING

        return BoilerMode.MIXED
