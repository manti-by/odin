"""Talk to the local ebusd daemon over its TCP text protocol."""

from __future__ import annotations

import fcntl
import socket
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from django.conf import settings


class EbusdError(Exception):
    """ebusd returned an error or could not be reached."""


@contextmanager
def lock_state(lock_path: Path) -> Iterator[None]:
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
