from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from django.utils import timezone

from odin.apps.relays.models import RelayState, RelayType


if TYPE_CHECKING:
    from odin.apps.relays.models import Relay


class RelayTargetStateService:
    def __init__(self, relay: Relay):
        self.relay = relay

    def get_current_period_from_schedule(self) -> dict | None:
        schedule = self.relay.context.get("schedule", {})
        if not (periods := schedule.get("periods", [])):
            return None

        current_time = timezone.localtime().time()
        for period in periods:
            try:
                start_time = timezone.datetime.strptime(period["start_time"], "%H:%M").time()
                end_time = timezone.datetime.strptime(period["end_time"], "%H:%M").time()
            except (KeyError, ValueError):
                continue

            if start_time <= end_time and start_time <= current_time <= end_time:
                return period
            elif current_time >= start_time or current_time <= end_time:
                return period

        return None

    def get_pump_target_state(self) -> str:
        if period := self.get_current_period_from_schedule():
            if "target_state" in period:
                return period["target_state"]
        return self.relay.state

    def get_servo_target_state(self) -> str:
        if not self.relay.sensor or self.relay.sensor.temp is None:
            return RelayState.UNKNOWN

        target_temp = self.relay.sensor.target_temp
        if period := self.get_current_period_from_schedule():
            if period.get("target_temp"):
                target_temp = Decimal(str(period["target_temp"]))

        if self.relay.sensor.temp < target_temp - self.relay.sensor.temp_hysteresis:
            return RelayState.ON

        if self.relay.sensor.temp > target_temp + self.relay.sensor.temp_hysteresis:
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
