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

    def get_pump_target_state(self) -> RelayState.choices:
        if self.relay.type != RelayType.PUMP:
            raise ValidationError(f"Relay type {self.relay.type} is not supported")

        now = timezone.localtime()
        day, hour = now.strftime("%w"), now.strftime("%H")

        state = self.relay.context.get("schedule", {}).get(day, {}).get(hour)
        if state is not None:
            return RelayState.ON if state else RelayState.OFF
        return RelayState.UNKNOWN

    def get_servo_target_state(self) -> RelayState.choices:
        if self.relay.type != RelayType.SERVO:
            raise ValidationError(f"Relay type {self.relay.type} is not supported")

        if not self.relay.sensor or self.relay.sensor.temp is None:
            return RelayState.UNKNOWN

        target_temp_min = self.relay.sensor.target_temp - self.relay.sensor.temp_hysteresis
        target_temp_max = self.relay.sensor.target_temp + self.relay.sensor.temp_hysteresis

        if target_temp_min < self.relay.sensor.temp < target_temp_max:
            return RelayState.OFF
        return RelayState.ON

    def get_target_state(self) -> RelayState.choices:
        if self.relay.force_state is not None:
            return self.relay.force_state

        match self.relay.type:
            case RelayType.PUMP:
                return self.get_pump_target_state()
            case RelayType.SERVO:
                return self.get_servo_target_state()
            case _:
                return RelayState.UNKNOWN
