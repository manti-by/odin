---
title: 'Midseason pump cadence — 30 minutes every 2 hours'
date: '2026-10-11'
type: implementation
status: resolved
session_id: ses_midseason_pump_cadence_2026_10_11
services: [relays-services, test_relays, AGENTS]
branch: master
tickets: []
tags: [relays, midseason, pump, schedule, tests]
related: [2026-09-19-mnt-215-midseason-mode, 2026-09-23-relay-mode-compute-on-read,
  2026-09-18-relay-state-mode-refactor]
---

# Midseason pump cadence — 30 minutes every 2 hours

## TL;DR

Changed the midseason pump duty cycle from *1 hour every 3 hours* to *30 minutes every 2 hours*:
the pump now runs 6:00–6:30, 8:00–8:30, 10:00–10:30 and so on. The night guard (`hour >= 6`) was
kept, so hours 0–5 still never heat in midseason. Servo behavior is untouched — servos stay
`(OFF, MIDSEASON)` for the whole midseason window. All 98 relay tests pass.

## Overview

Midseason is the band `8 < outside_temp < 15` in
`odin/apps/relays/services.py`. Both the pump and servo branches are keyed off that single
condition; only the pump branch had a time-based cadence.

The whole change is one predicate. No model field, migration, or frontend change was needed —
the cadence is computed on read by `RelayTargetStateService.get_target_state()`.

## Step 1 — Pump cadence in `odin/apps/relays/services.py`

Before — active for the whole of every third hour, any minute:

```python
elif 8 < outside_temp < 15:
    # Midseason mode, should work for 1 hour every 3rd hour, but not at night
    if self.now.hour >= 6 and self.now.hour % 3 == 0:
        return RelayState.ON, RelayMode.MIDSEASON
    return RelayState.OFF, RelayMode.MIDSEASON
```

After — first 30 minutes of every even hour, still daytime only:

```python
elif 8 < outside_temp < 15:
    # Midseason mode, should work for 30 minutes every 2nd hour, but not at night
    if self.now.hour >= 6 and self.now.hour % 2 == 0 and self.now.minute < 30:
        return RelayState.ON, RelayMode.MIDSEASON
    return RelayState.OFF, RelayMode.MIDSEASON
```

Notes on the predicate:

- **Window alignment** — `hour % 2 == 0` anchors the cycle to even wall-clock hours, matching the
  requested 2:00/4:00/… cadence rather than a rolling 2-hour period from midnight.
- **`minute < 30`** — a half-open interval `[H:00, H:30)`, so the pump is off from `:30` onward.
- **Day guard unchanged** — confirmed with the user that hours 0–5 stay off; the example
  "2:00–2:30, 4:00–4:30" describes the cadence shape, not a request to heat at night.
- Servo branch (`services.py:132-134`) is deliberately untouched: midseason always returns
  `(OFF, MIDSEASON)`, so a servo never closes while the pump cycles.

## Step 2 — Tests in `odin/tests/models/test_relays.py`

Existing midseason tests were pinned to the old cadence and had to be re-timed. They patch
`odin.apps.relays.services.timezone.localtime` to a fixed `datetime`, which is what makes the
`now.hour` / `now.minute` fields testable at all.

- **`test_relays__pump_runs_first_half_hour_of_every_second_hour_in_midseason`** (was
  `..._runs_every_third_hour_...`) — now asserts `08:05 → ON`.
- **`test_relays__pump_is_off_outside_every_second_hour_in_midseason`** (was
  `..._outside_every_third_hour_...`) — asserts `08:45 → OFF`, covering the second half of an
  *active* hour, not just an idle hour.
- **`test_relays__pump_midseason_cadence_by_hour`** — the parametrize table was rewritten. It
  previously pinned `minute=30` for every case, which under the new rule is always `OFF`; it now
  pins `minute=5` and asserts even hours are `ON`, odd hours and hours 0–5 are `OFF`
  (0, 3, 5 → `OFF`; 6 → `ON`; 7, 9 → `OFF`; 20 → `ON`; 21, 23 → `OFF`).
- **`test_relays__pump_midseason_active_window_spans_first_half_hour`** — renamed from
  `..._spans_full_hour`; parametrize narrowed to `(0, 10, 29)`, all `ON`.
- **`test_relays__pump_midseason_is_off_in_second_half_hour`** — new, parametrize
  `(30, 45, 59)`, all `OFF`. The old suite had no assertion that the window ever *ends*.
- Servo midseason tests were only renamed/retimed for consistency; their expectations are all
  `OFF` and are insensitive to the cadence.

## Step 3 — `AGENTS.md`

The relay-control section documented the old predicate verbatim; refreshed to
`hour >= 6 and hour % 2 == 0 and minute < 30`.

## Test Results

- `uv run pytest --ds=odin.settings.test odin/tests/models/test_relays.py odin/tests/api/test_relays.py`
  → **98 passed**.

---

## Follow-ups

- The cadence is hardcoded in the service rather than exposed via the relay `context` /
  schedule structure that MNT-217 added. If midseason timing ever needs to be per-relay or
  user-tunable, promote it to the same `schedule` dict instead of widening the predicate.
- Midnight-anchored cycles are visible to consumers only as `MIDSEASON` mode; the dashboard does
  not surface the on/off countdown.

## References

- Related: [[2026-09-19-mnt-215-midseason-mode]]
- Related: [[2026-09-23-relay-mode-compute-on-read]]
- Related: [[2026-09-18-relay-state-mode-refactor]]
