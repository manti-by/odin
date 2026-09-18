"""Weekly hot-water boil schedule constants and next-run computation.

The Protherm Lynx 25 runs a weekly hot-water cycle: a 55 °C boil on Saturday at
01:00, cleared again at 02:00. The schedule is not persisted yet, so the next
occurrence is computed from the current local time.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from django.utils import timezone


BOIL_WEEKDAY = 5  # Saturday (Monday = 0)
BOIL_HOUR = 1
CLEAR_HOUR = 2


def get_next_boil_schedule() -> tuple[datetime, datetime]:
    """Return the next (boil, clear) datetimes in the current timezone."""
    now = timezone.localtime()
    days_ahead = (BOIL_WEEKDAY - now.weekday()) % 7
    boil = (now + timedelta(days=days_ahead)).replace(hour=BOIL_HOUR, minute=0, second=0, microsecond=0)
    clear = boil + timedelta(hours=CLEAR_HOUR - BOIL_HOUR)
    if clear <= now:
        return boil + timedelta(days=7), clear + timedelta(days=7)
    if boil <= now:
        return boil + timedelta(days=7), clear
    return boil, clear
