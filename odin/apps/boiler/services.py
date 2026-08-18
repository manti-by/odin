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

import logging
import socket
from pathlib import Path

from django.conf import settings


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
                        break
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
        self._write(values)
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self.state_file.write_text(f"{values}\n")
        logger.info(f"Boiler SetMode sent and saved as override: {values}")
        return values

    def _write(self, values: str) -> None:
        # SETMODE_DEF and values contain no spaces, so no quoting is needed.
        self.client.command(f"write -def {SETMODE_DEF} {values}")

    @staticmethod
    def _temp(value: int | None) -> str:
        if value is None:
            return NOT_CONTROLLED
        if not 0 <= value <= MAX_TEMP:
            raise ValueError(f"temperature {value} out of range 0..{MAX_TEMP} °C")
        return str(int(value))
