from __future__ import annotations

import copy
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from django.utils import timezone

from odin.apps.relays.models import RelayLog, RelayMode, RelayState, RelayType
from odin.apps.weather.models import Weather


if TYPE_CHECKING:
    from django.contrib.auth.models import User

    from odin.apps.relays.models import Relay


class RelayLogService:
    """Audit trail for relay state, mode, force_state and context changes."""

    TRACKED_FIELDS = ("state", "mode", "force_state", "context")

    def __init__(self, relay: Relay, user: User | None = None):
        self.relay = relay
        self.user = user

    @classmethod
    def snapshot(cls, relay: Relay) -> dict[str, Any]:
        """Capture the tracked fields before a mutation."""
        return {
            field: copy.deepcopy(getattr(relay, field)) if field == "context" else getattr(relay, field)
            for field in cls.TRACKED_FIELDS
        }

    def log_change(self, before: dict[str, Any]) -> RelayLog | None:
        """Create a RelayLog row when any tracked field differs from the snapshot.

        Args:
            before: snapshot of the relay taken before the change.

        Returns:
            The created RelayLog, or None when nothing changed.
        """
        after = self.snapshot(self.relay)
        if all(before.get(field) == after[field] for field in self.TRACKED_FIELDS):
            return None

        return RelayLog.objects.create(
            relay=self.relay,
            old_state=before.get("state"),
            new_state=after["state"],
            old_mode=before.get("mode"),
            new_mode=after["mode"],
            old_force_state=before.get("force_state"),
            new_force_state=after["force_state"],
            old_context=before.get("context") or {},
            new_context=after["context"] or {},
            updated_by=self.user,
        )


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

            if start_time <= end_time and start_time <= current_time < end_time:
                return period
            elif end_time < start_time and (current_time >= start_time or current_time < end_time):
                return period

        return None

    def get_pump_target_state(self) -> tuple[RelayState, RelayMode]:
        # Check outside temp to decide what mode to use
        if self.weather and (outside_temp := self.weather.temp) is not None:
            # Summer mode, disable everything
            if outside_temp >= 15:
                # Summer mode, always off
                return RelayState.OFF, RelayMode.SUMMER
            elif outside_temp < -8:
                # Anti freeze mode, always on
                return RelayState.ON, RelayMode.ANTIFREEZE
            elif 8 < outside_temp < 15:
                # Midseason mode, should work for 1 hour every 3rd hour, but not at night
                if self.now.hour >= 6 and self.now.hour % 3 == 0:
                    return RelayState.ON, RelayMode.MIDSEASON
                return RelayState.OFF, RelayMode.MIDSEASON

        # Default target state from schedule
        if period := self.get_current_period_from_schedule():
            if "target_state" in period:
                return period["target_state"], RelayMode.BASIC

        return RelayState.ON, RelayMode.FALLBACK

    def get_servo_target_state(self) -> tuple[RelayState, RelayMode]:
        # Open circuit if no sensor data
        sensor = self.relay.sensor
        if not sensor or not sensor.is_alive or sensor.temp is None:
            return RelayState.OFF, RelayMode.UNKNOWN

        # If related pump is OFF also do not close a servo
        if related_relay := self.relay.related_relay:
            if related_relay.is_pump and not related_relay.is_on:
                return RelayState.OFF, RelayMode.IGNORED

        # Check outside temp to decide what mode to use
        if self.weather and (outside_temp := self.weather.temp) is not None:
            # Summer mode, disable everything
            if outside_temp >= 15:
                # Summer mode, do not close
                return RelayState.OFF, RelayMode.SUMMER
            elif outside_temp < -8:
                # Anti freeze mode, do not close
                return RelayState.OFF, RelayMode.ANTIFREEZE
            elif 8 < outside_temp < 15:
                # Midseason mode, servos are always open
                return RelayState.OFF, RelayMode.MIDSEASON

        # Get target temp from schedule
        target_temp = sensor.target_temp
        if period := self.get_current_period_from_schedule():
            if period.get("target_temp") is not None:
                target_temp = Decimal(str(period["target_temp"]))

        # No target temperature configured, nothing to regulate against
        if target_temp is None or sensor.temp_hysteresis is None:
            return RelayState.OFF, RelayMode.UNKNOWN

        if sensor.temp < target_temp - sensor.temp_hysteresis:
            return RelayState.ON, RelayMode.BASIC

        if sensor.temp > target_temp + sensor.temp_hysteresis:
            return RelayState.OFF, RelayMode.BASIC

        return RelayState.OFF, RelayMode.FALLBACK

    def get_target_state(self) -> tuple[RelayState, RelayMode]:
        if self.relay.force_state is not None:
            return self.relay.force_state, RelayMode.FORCED

        match self.relay.type:
            case RelayType.PUMP:
                return self.get_pump_target_state()
            case RelayType.SERVO:
                return self.get_servo_target_state()
            case _:
                return RelayState.UNKNOWN, RelayMode.FALLBACK
