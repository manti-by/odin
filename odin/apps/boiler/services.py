"""Control the Protherm Lynx 25 MKO boiler (Vaillant BAI00) through the local ebusd daemon.

The boiler is driven with the Vaillant ``SetMode`` message (ZZ=08, PB SB=b510,
submessage ID=00, 9 data bytes). The stock ebusd config marks SetMode as passive
(``uw``), so writes are sent with ``write -def`` using an active-write copy of the
definition; ebusd must therefore run with ``--enabledefine``.

The boiler keeps the hot-water setpoint after a single write, but treats the
override as a live controller feed: a periodic ``refresh()`` (see the
boiler-refresh.timer systemd unit) keeps long-running heating overrides applied.
"""

from __future__ import annotations

import fcntl
import logging
import os
import socket
import tempfile
from collections.abc import Callable
from contextlib import contextmanager
from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.db import models

from odin.apps.relays.models import Relay, RelayState, RelayType
from odin.apps.relays.services import RelayTargetStateService
from odin.apps.weather.models import Weather


logger = logging.getLogger(__name__)

# Active-write copy of the passive "bai SetMode" definition from vaillant/bai.308523.inc.
SETMODE_DEF = (
    "w,bai,SetModeOverride,,,08,b510,00,"
    "hcmode,,UCH,0=auto;1=off;2=heat;3=water,,,"
    "flowtempdesired,,D1C,,,,"
    "hwctempdesired,,D1C,,,,"
    "hwcflowtempdesired,,UCH,,,,"
    ",,IGN:1,,,,"
    "disablehc,,BI0,,,,"
    "disablehwctapping,,BI1,,,,"
    "disablehwcload,,BI2,,,,"
    ",,IGN:1,,,,"
    "remotecontrolhcpump,,BI0,,,,"
    "releasebackup,,BI1,,,,"
    "releasecooling,,BI2,,,"
)

# Sends the field's replacement value (0xFF) = "not controlled": the boiler
# falls back to its own panel setpoint for that field.
NOT_CONTROLLED = "-"

MAX_TEMP = 80


class EbusdError(Exception):
    """ebusd returned an error or could not be reached."""


@contextmanager
def lock_state(lock_path: Path):
    """Hold an exclusive interprocess lock shared with /usr/local/bin/boiler-set."""
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+") as fh:
        fcntl.flock(fh.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(fh.fileno(), fcntl.LOCK_UN)


class EbusdClient:
    """Minimal client for ebusd's TCP text protocol (one command per connection)."""

    def __init__(self, host: str | None = None, port: int | None = None, timeout: float = 15):
        self.host = host or settings.EBUSD_HOST
        self.port = port or settings.EBUSD_PORT
        self.timeout = timeout

    def command(self, command: str) -> str:
        """Send one command line and return the response (terminated by an empty line)."""
        try:
            with socket.create_connection((self.host, self.port), timeout=self.timeout) as conn:
                conn.sendall(command.encode() + b"\n")
                raw = b""
                while not raw.endswith(b"\n\n"):
                    chunk = conn.recv(4096)
                    if not chunk:
                        raise EbusdError(f"{command!r} got EOF before the response terminated")
                    raw += chunk
        except OSError as e:
            raise EbusdError(f"cannot talk to ebusd at {self.host}:{self.port}: {e}") from e

        response = raw.decode().strip()
        if response.startswith("ERR:"):
            raise EbusdError(f"{command!r} failed: {response}")
        return response


class BoilerService:
    """Set the boiler's operating mode and setpoints, and read its live state."""

    STATUS_FIELDS = (
        ("FlowTempDesired", "heating flow setpoint, °C"),
        ("HwcTempDesired", "hot-water setpoint, °C"),
        ("StorageTempDesired", "tank setpoint, °C"),
        ("FlowTemp", "actual flow, °C"),
        ("ReturnTemp", "actual return, °C"),
        ("StorageTemp", "actual tank, °C"),
        ("ModulationDesired", "burner modulation, %"),
        ("Status01", "flow;return;outside;hwc;storage;pump"),
        ("Status02", "hwcmode;... (does not echo the commanded mode)"),
    )

    def __init__(self, client: EbusdClient | None = None):
        self.client = client or EbusdClient()
        self.state_file = Path(settings.BOILER_STATE_FILE)
        self.lock_file = Path(settings.BOILER_LOCK_FILE)

    def set_boiling(self, hwc_temp: int) -> str:
        """Hot water only: SetMode water (the flow field is ignored by the boiler in this mode)."""
        return self._set_mode("water", flow_temp=0, hwc_temp=hwc_temp)

    def set_heating(self, flow_temp: int) -> str:
        """Heating only: SetMode heat; hot water falls back to the panel setpoint."""
        return self._set_mode("heat", flow_temp=flow_temp, hwc_temp=None)

    def set_mixed(self, flow_temp: int, hwc_temp: int) -> str:
        """Heating + hot water: SetMode auto with both setpoints active."""
        return self._set_mode("auto", flow_temp=flow_temp, hwc_temp=hwc_temp)

    def set_off(self) -> str:
        """Both circuits off."""
        return self._set_mode("off", flow_temp=0, hwc_temp=0)

    def refresh(self) -> str | None:
        """Re-send the last override (called by boiler-refresh.timer); None when no override is active."""
        with lock_state(self.lock_file):
            try:
                values = self.state_file.read_text().strip()
            except FileNotFoundError:
                return None
            if not values:
                return None
            self._write(values)
            return values

    def clear_override(self) -> None:
        """Drop the override; the boiler falls back to its panel settings within a few minutes."""
        with lock_state(self.lock_file):
            self.state_file.unlink(missing_ok=True)
        logger.info("Boiler override cleared")

    def current_override(self) -> str | None:
        try:
            return self.state_file.read_text().strip() or None
        except FileNotFoundError:
            return None

    def read_field(self, name: str) -> str:
        """Read a bai field fresh from the bus (not from ebusd's cache)."""
        return self.client.command(f"read -f -c bai {name}")

    def status(self) -> dict[str, str]:
        result = {}
        for name, _note in self.STATUS_FIELDS:
            try:
                result[name] = self.read_field(name)
            except EbusdError as e:
                result[name] = f"error: {e}"
        return result

    def _set_mode(self, hcmode: str, flow_temp: int | None, hwc_temp: int | None) -> str:
        values = ";".join(
            (
                hcmode,
                self._temp(flow_temp),
                self._temp(hwc_temp),
                NOT_CONTROLLED,  # hwcflowtempdesired
                "0;0;0",  # disablehc / disablehwctapping / disablehwcload
                "0;0;0",  # remotecontrolhcpump / releasebackup / releasecooling
            )
        )
        with lock_state(self.lock_file):
            self._write(values)
            self._save_state(values)
        logger.info(f"Boiler SetMode sent and saved as override: {values}")
        return values

    def _write(self, values: str) -> None:
        # SETMODE_DEF and values contain no spaces, so no quoting is needed.
        self.client.command(f"write -def {SETMODE_DEF} {values}")

    def _save_state(self, values: str) -> None:
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=self.state_file.parent, prefix=self.state_file.name, suffix=".tmp")
        try:
            with os.fdopen(fd, "w") as fh:
                fh.write(f"{values}\n")
            os.replace(tmp, self.state_file)
        except Exception:
            os.unlink(tmp)
            raise

    @staticmethod
    def _temp(value: int | None) -> str:
        if value is None:
            return NOT_CONTROLLED
        if not 0 <= value <= MAX_TEMP:
            raise ValueError(f"temperature {value} out of range 0..{MAX_TEMP} °C")
        return str(int(value))


SUMMER_TEMP_THRESHOLD = Decimal("15")
ANTIFREEZE_TEMP_THRESHOLD = Decimal("-8")
MIDSEASON_TEMP_LOWER = Decimal("8")
DEFAULT_HEATING_FLOW_TEMP = 55
DEFAULT_HWC_TEMP = 45


class BoilerMode(models.TextChoices):
    HEATING = "heating", "Heating"
    MIXED = "mixed", "Mixed"
    OFF = "off", "Off"
    CLEAR_OVERRIDE = "clear_override", "Clear override"


class BoilerModeController:
    """Map aggregated pump/servo states and outside temperature onto boiler modes.

    Cross-cutting service between the relays/weather domain and :class:`BoilerService`.
    On every run it yields to an active boiling override, skips when no outside
    temperature is available, aggregates the target state of every active pump and
    servo through :class:`~odin.apps.relays.services.RelayTargetStateService`, and
    applies the boiler mode for the current weather band.

    Decision matrix (``t`` is the current outside temperature, °C):

    * ``t >= 15`` (summer) -> ``set_off``: the relay service's "disable everything" band;
    * ``t < -8`` (anti-freeze) -> ``set_heating``: keep the system above freezing;
    * ``-8 <= t < 8`` with pump and servo on -> ``set_mixed``: heating plus hot water;
    * ``8 <= t < 15`` with pump and servo on -> ``set_heating``: heating only;
    * no heating demand -> ``set_off``;
    * unknown pump/servo state -> ``clear_override``: let the panel take over.

    An active boiling override (``water`` mode in :meth:`BoilerService.current_override`)
    always wins so the scheduled hot-water cycle is never fought.
    """

    def __init__(
        self,
        boiler_service: BoilerService | None = None,
        relay_target_state_factory: Callable[[Relay], RelayTargetStateService] | None = None,
    ) -> None:
        self.boiler_service = boiler_service or BoilerService()
        self.relay_target_state_factory = relay_target_state_factory or RelayTargetStateService

    def run(self) -> str | None:
        """Decide the boiler mode and apply it, returning the written values or None when skipped."""
        if self._is_boil_override_active():
            logger.info("Boiling override active, leaving the boiler mode untouched")
            return None

        outside_temp = self._outside_temp()
        if outside_temp is None:
            logger.info("No outside temperature available, leaving the boiler mode untouched")
            return None

        pump_state = self._aggregate_state(RelayType.PUMP)
        servo_state = self._aggregate_state(RelayType.SERVO)

        mode = self._decide_mode(pump_state, servo_state, outside_temp)
        logger.info(f"Boiler mode decided: {mode} (outside {outside_temp} °C, pump {pump_state}, servo {servo_state})")
        return self._apply(mode)

    def _apply(self, mode: BoilerMode) -> str | None:
        match mode:
            case BoilerMode.HEATING:
                return self.boiler_service.set_heating(DEFAULT_HEATING_FLOW_TEMP)
            case BoilerMode.MIXED:
                return self.boiler_service.set_mixed(DEFAULT_HEATING_FLOW_TEMP, DEFAULT_HWC_TEMP)
            case BoilerMode.OFF:
                return self.boiler_service.set_off()
            case _:
                self.boiler_service.clear_override()
                return None

    def _decide_mode(self, pump_state: RelayState, servo_state: RelayState, outside_temp: Decimal) -> BoilerMode:
        if pump_state == RelayState.UNKNOWN or servo_state == RelayState.UNKNOWN:
            return BoilerMode.CLEAR_OVERRIDE

        if outside_temp >= SUMMER_TEMP_THRESHOLD:
            return BoilerMode.OFF

        if outside_temp < ANTIFREEZE_TEMP_THRESHOLD:
            return BoilerMode.HEATING

        if pump_state == RelayState.ON and servo_state == RelayState.ON:
            if outside_temp < MIDSEASON_TEMP_LOWER:
                return BoilerMode.MIXED
            return BoilerMode.HEATING

        return BoilerMode.OFF

    def _aggregate_state(self, relay_type: RelayType) -> RelayState:
        states = [
            RelayState(self.relay_target_state_factory(relay).get_target_state())
            for relay in Relay.objects.active().filter(type=relay_type)
        ]
        if any(state == RelayState.ON for state in states):
            return RelayState.ON
        if states and all(state == RelayState.OFF for state in states):
            return RelayState.OFF
        return RelayState.UNKNOWN

    def _outside_temp(self) -> Decimal | None:
        weather = Weather.objects.current()
        if weather is None:
            return None
        return weather.temp

    def _is_boil_override_active(self) -> bool:
        override = self.boiler_service.current_override()
        return bool(override and override.split(";", 1)[0] == "water")
