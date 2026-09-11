from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from django.utils import timezone

from odin.apps.relays.models import RelayState, RelayType
from odin.apps.weather.models import Weather


if TYPE_CHECKING:
    from odin.apps.relays.models import Relay


class RelayTargetStateService:
    def __init__(self, relay: Relay):
        self.relay = relay
        self.weather = Weather.objects.current()
        self.now = timezone.localtime()

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
            elif end_time <= start_time and (current_time >= start_time or current_time <= end_time):
                return period

        return None

    def get_pump_target_state(self) -> str:
        # Check outside temp to decide what mode to use
        if self.weather and (outside_temp := self.weather.temp) is not None:
            # Summer mode, disable everything
            if outside_temp >= 15:
                # Summer mode, always off
                return RelayState.OFF
            elif outside_temp < -8:
                # Anti freeze mode, always on
                return RelayState.ON
            elif 8 < outside_temp < 15:
                # Midseason mode, should work for 10 mins every hour
                if self.now.minute < 10:
                    return RelayState.ON
                return RelayState.OFF

        # Default target state from schedule
        if period := self.get_current_period_from_schedule():
            if "target_state" in period:
                return period["target_state"]

        return RelayState.ON

    def get_servo_target_state(self) -> str:
        # Open circuit if no sensor data
        sensor = self.relay.sensor
        if not sensor or not sensor.is_alive or sensor.temp is None:
            return RelayState.OFF

        # Check forced state
        if self.relay.force_state is not None:
            return self.relay.force_state

        # If related pump is OFF also switch off a servo
        if related_relay := self.relay.related_relay:
            if related_relay.is_pump and not related_relay.is_on:
                return RelayState.OFF

        # Check outside temp to decide what mode to use
        if self.weather and (outside_temp := self.weather.temp) is not None:
            # Summer mode, disable everything
            if outside_temp >= 15:
                # Summer mode, do not close
                return RelayState.OFF
            elif outside_temp < -8:
                # Anti freeze mode, do not close
                return RelayState.OFF
            elif 8 < outside_temp < 15:
                # Midseason mode, must work for 10 mins every hour
                if self.now.minute < 10:
                    return RelayState.OFF

        # Get target temp from schedule
        target_temp = sensor.target_temp
        if period := self.get_current_period_from_schedule():
            if period.get("target_temp"):
                target_temp = Decimal(str(period["target_temp"]))

        # No target temperature configured, nothing to regulate against
        if target_temp is None:
            return RelayState.OFF

        if sensor.temp < target_temp - sensor.temp_hysteresis:
            return RelayState.ON

        if sensor.temp > target_temp + sensor.temp_hysteresis:
            return RelayState.OFF

        return RelayState.OFF

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
