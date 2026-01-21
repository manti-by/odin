from __future__ import annotations

from typing import TYPE_CHECKING

from django.core.exceptions import ValidationError
from django.utils import timezone

from odin.apps.relays.models import RelayState, RelayType


if TYPE_CHECKING:
    from odin.apps.relays.models import Relay


class RelayTargetStateService:
    def __init__(self, relay: Relay):
        self.relay = relay

    def get_pump_target_state(self) -> str:
        if self.relay.type != RelayType.PUMP:
            raise ValidationError(f"Relay type {self.relay.type} is not supported")

        now = timezone.localtime()
        day, hour = now.strftime("%w"), now.strftime("%H")

        state = self.relay.context.get("schedule", {}).get(day, {}).get(hour)
        if state is not None:
            return RelayState.ON if state else RelayState.OFF

        return self.relay.state

    def get_servo_target_state(self) -> str:
        if self.relay.type != RelayType.SERVO:
            raise ValidationError(f"Relay type {self.relay.type} is not supported")

        if not self.relay.sensor or self.relay.sensor.temp is None:
            return RelayState.UNKNOWN

        target_temp, hysteresis = self.relay.sensor.target_temp, self.relay.sensor.temp_hysteresis

        if self.relay.sensor.temp < target_temp - hysteresis:
            return RelayState.ON

        if self.relay.sensor.temp > target_temp + hysteresis:
            return RelayState.OFF

        return self.relay.state

    def get_target_state(self) -> str:
        if self.relay.force_state is not None:
            return str(self.relay.force_state)

        match self.relay.type:
            case RelayType.PUMP:
                return self.get_pump_target_state()
            case RelayType.SERVO:
                return self.get_servo_target_state()
            case _:
                return RelayState.UNKNOWN
