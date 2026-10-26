import copy
from decimal import Decimal
from enum import Enum, auto
from typing import TYPE_CHECKING, Any

from django.utils import timezone

from odin.apps.relays.models import RelayLog, RelayMode, RelayState, RelayType
from odin.apps.weather.services import apparent_temp, get_latest_weather


if TYPE_CHECKING:
    from django.contrib.auth.models import User

    from odin.apps.relays.models import Relay


class WeatherMode(Enum):
    """Outside weather classification driving the relay rules.

    Kept apart from `RelayMode` so "no usable weather" stays distinct from the `-8 … 10 °C` default
    band: they only share the `ANTIFREEZE` label, and only where a mode is reported.
    """

    NONE = auto()
    ANTIFREEZE = auto()
    DEFAULT = auto()
    MIDSEASON = auto()
    SUMMER = auto()


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
    ANTIFREEZE_TEMP = Decimal("-8")
    MIDSEASON_TEMP_MIN = Decimal("10")
    SUMMER_TEMP_MIN = Decimal("17")
    MIDSEASON_EXTENDED_TEMP_MAX = Decimal("20")

    def __init__(self, relay: Relay):
        self.relay = relay
        self.weather = get_latest_weather()
        self.now = timezone.localtime()

    def is_cycle_window(self) -> bool:
        """Whether the relay must be forced into its open circuit position for the current cycle slot.

        A half-open [H:00, H:30) on even local hours, anchored at local midnight. Unlike midseason
        there is no night guard: the cycle runs around the clock.
        """
        return self.now.hour % 2 == 0 and self.now.minute < 30

    def get_current_period(self, schedule: dict) -> dict | None:
        """Return the period covering the current local time, or None.

        Periods are half-open `[start_time, end_time)` and may span midnight. Malformed entries are
        skipped rather than raised: `context` is a free-form JSON column that can be edited by hand.
        """
        if not isinstance(schedule, dict) or not isinstance(periods := schedule.get("periods"), list):
            return None

        current_time = timezone.localtime().time()
        for period in periods:
            if not isinstance(period, dict):
                continue
            try:
                start_time = timezone.datetime.strptime(period["start_time"], "%H:%M").time()
                end_time = timezone.datetime.strptime(period["end_time"], "%H:%M").time()
            except KeyError, TypeError, ValueError:
                continue

            if start_time <= end_time and start_time <= current_time < end_time:
                return period
            elif end_time < start_time and (current_time >= start_time or current_time < end_time):
                return period

        return None

    def get_context(self) -> dict:
        """Return the relay context as a dict.

        `context` is a free-form JSON column, so a hand-edited value may be a list, a string or
        null; those are treated as empty instead of raising on `.get()`.
        """
        return self.relay.context if isinstance(self.relay.context, dict) else {}

    def get_current_period_from_schedule(self) -> dict | None:
        return self.get_current_period(self.get_context().get("schedule", {}))

    def get_current_override_period(self) -> dict | None:
        """Return the override period covering now, or None.

        Periods without an `ON`/`OFF` `target_state` are dropped before the lookup, so a later
        overlapping valid period still applies instead of the override being silently ignored.
        """
        schedule = self.get_context().get("override_schedule", {})
        if isinstance(schedule, dict) and isinstance(periods := schedule.get("periods"), list):
            schedule = {
                "periods": [
                    period
                    for period in periods
                    if isinstance(period, dict) and period.get("target_state") in RelayState.active_values()
                ]
            }
        return self.get_current_period(schedule)

    def get_weather_mode(self) -> WeatherMode:
        """Classify the current weather into the mode that drives the relay rules.

        Missing weather and the whole `-8 … 10 °C` gap are different things: only the former is
        `WeatherBand.NONE`, which is what the antifreeze fail-safe keys off. Antifreeze and the
        lower midseason edge stay on the raw temperature, so the fail-safe heat answer never depends
        on fetched humidity/wind. Above `SUMMER_TEMP_MIN` the Steadman apparent temperature extends
        midseason up to `MIDSEASON_EXTENDED_TEMP_MAX`, so a windy warm day keeps cycling radiators.
        """
        if not self.weather or (outside_temp := self.weather.temp) is None:
            return WeatherMode.NONE

        if outside_temp < self.ANTIFREEZE_TEMP:
            return WeatherMode.ANTIFREEZE

        if outside_temp < self.MIDSEASON_TEMP_MIN:
            return WeatherMode.DEFAULT

        if outside_temp < self.SUMMER_TEMP_MIN:
            return WeatherMode.MIDSEASON

        feels_like = apparent_temp(outside_temp, self.weather.humidity, self.weather.wind_speed)
        extended_midseason = (
            outside_temp < self.MIDSEASON_EXTENDED_TEMP_MAX
            and feels_like is not None
            and feels_like < self.SUMMER_TEMP_MIN
        )
        return WeatherMode.MIDSEASON if extended_midseason else WeatherMode.SUMMER

    @staticmethod
    def invert_state(state: RelayState) -> RelayState:
        """Flip the logical state for a servo circuit, whose `ON` closes the circuit."""
        return RelayState.OFF if state == RelayState.ON else RelayState.ON

    def get_manual_target_state(self, invert: bool = False) -> tuple[RelayState, RelayMode] | None:
        """Return the operator-requested state: `force_state`, else the active override period.

        Pumps and servos call this after the antifreeze fail-safe, so a manual stop never wins over
        the freeze protection. `invert` flips the state for servos: a logical `ON` (heat) opens the
        circuit, a logical `OFF` (stop) closes it.

        Returns:
            The forced or overridden state and its mode, or None when neither applies.
        """
        if (force_state := self.relay.force_state) in RelayState.active_values():
            state = RelayState(force_state)
            return self.invert_state(state) if invert else state, RelayMode.FORCED

        if period := self.get_current_override_period():
            if (override_state := period.get("target_state")) in RelayState.active_values():
                state = RelayState(override_state)
                return self.invert_state(state) if invert else state, RelayMode.OVERRIDE

        return None

    def get_pump_target_state(self, weather_mode: WeatherMode) -> tuple[RelayState, RelayMode]:
        # Missing weather and real antifreeze both call for heat, and outrank any manual input
        if weather_mode in (WeatherMode.NONE, WeatherMode.ANTIFREEZE):
            return RelayState.ON, RelayMode.ANTIFREEZE

        # Forced state and override schedule outrank the weather rules below
        if manual := self.get_manual_target_state():
            return manual

        # Do not activate pumps at Summer
        if weather_mode == WeatherMode.SUMMER:
            return RelayState.OFF, RelayMode.SUMMER

        # Midseason mode, should work for 30 minutes every 2nd hour, but not at night
        if weather_mode == WeatherMode.MIDSEASON:
            if self.now.hour >= 6 and self.is_cycle_window():
                return RelayState.ON, RelayMode.MIDSEASON
            return RelayState.OFF, RelayMode.MIDSEASON

        # Schedule branch, forced open circuit for 30 minutes every 2 hours
        if self.is_cycle_window():
            return RelayState.ON, RelayMode.CYCLE

        # Default target state from schedule
        if period := self.get_current_period_from_schedule():
            if "target_state" in period:
                return period["target_state"], RelayMode.BASIC

        return RelayState.ON, RelayMode.FALLBACK

    def get_servo_target_state(self, weather_mode: WeatherMode) -> tuple[RelayState, RelayMode]:
        # Open circuit if the linked sensor is missing, stale or has no reading
        sensor = self.relay.sensor
        if not sensor or not sensor.is_alive or sensor.temp is None:
            return RelayState.OFF, RelayMode.UNKNOWN

        # Missing weather and real antifreeze both call for heat, and outrank any manual input
        if weather_mode in (WeatherMode.NONE, WeatherMode.ANTIFREEZE):
            return RelayState.OFF, RelayMode.ANTIFREEZE

        # A servo must not close while its pump is off, not even for a forced or overridden close
        if related_relay := self.relay.related_relay:
            if related_relay.is_pump and not related_relay.is_on:
                return RelayState.OFF, RelayMode.IGNORED

        # Forced state and override schedule outrank the weather rules below
        if manual := self.get_manual_target_state(invert=True):
            return manual

        # Do not close servos at Summer or at Midseason
        if weather_mode == WeatherMode.SUMMER:
            return RelayState.OFF, RelayMode.SUMMER

        if weather_mode == WeatherMode.MIDSEASON:
            return RelayState.OFF, RelayMode.MIDSEASON

        # Schedule branch, forced open circuit for 30 minutes every 2 hours
        if self.is_cycle_window():
            return RelayState.OFF, RelayMode.CYCLE

        # Get target temp from schedule
        target_temp = sensor.target_temp
        if period := self.get_current_period_from_schedule():
            if period.get("target_temp") is not None:
                target_temp = Decimal(str(period["target_temp"]))

        # No target temperature configured, nothing to regulate against
        if target_temp is None or sensor.temp_hysteresis is None:
            return RelayState.OFF, RelayMode.UNKNOWN

        if sensor.temp < target_temp - sensor.temp_hysteresis:
            return RelayState.OFF, RelayMode.BASIC

        if sensor.temp > target_temp + sensor.temp_hysteresis:
            return RelayState.ON, RelayMode.BASIC

        return RelayState.OFF, RelayMode.FALLBACK

    def get_valve_target_state(self) -> tuple[RelayState, RelayMode]:
        """Valves are driven locally: weather is irrelevant, only explicit input applies."""
        if manual := self.get_manual_target_state():
            return manual

        return RelayState.UNKNOWN, RelayMode.FALLBACK

    def get_target_state(self) -> tuple[RelayState, RelayMode]:
        # Valves never read weather, so an unusable weather row must not break their rules
        if self.relay.type == RelayType.VALVE:
            return self.get_valve_target_state()

        weather_mode = self.get_weather_mode()
        match self.relay.type:
            case RelayType.PUMP:
                return self.get_pump_target_state(weather_mode=weather_mode)
            case RelayType.SERVO:
                return self.get_servo_target_state(weather_mode=weather_mode)
            case _:
                return self.get_valve_target_state()
