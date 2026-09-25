---
title: 'MNT-215: Midseason mode'
date: '2026-09-19'
type: implementation
status: resolved
session_id: ses_f47a82a55ffe6EHsQbDq9UIfPs
services: [Makefile, services, models, frontend, test_relays, pyproject, uv, .sessions, INDEX, 2026-09-19-mnt-215-midseason-mode]
branch: mnt-215-midseason-mode
tickets: [MNT-215]
tags: [wiki, feature, backend, frontend]
related: [2026-09-18-relay-state-mode-refactor, 2026-09-21-esp8266-indicator-icons]
---
# MNT-215: Midseason mode

## TL;DR

Midseason mode is activated every 3 hours for 1 hour, replacing the previous 10-minute activation every hour. The pump runs only inside the active hour and only during the day (`hour >= 6`); servos stay open (OFF) for the whole midseason window instead of inverting with the pump. The update was successfully implemented and all tests have passed. The change is reflected in the updated wiki page and Python files. The new logic uses the modulus operator to determine the activation time.

---

## Overview

The implementation updated the relay state service in `odin/apps/relays/services.py` to enable midseason mode every 3 hours for 1 hour. Key changes include updates to the `get_pump_target_state` and `get_servo_target_state` methods, as well as the addition of a new wiki page `wiki/pages/2026-09-19-mnt-215-midseason-mode.md` and test updates in `odin/tests/models/test_relays.py`. A later refinement scoped the pump activation to daytime hours (`hour >= 6`) and made servos unconditionally open during midseason.

## Changed files

- `Makefile` (6/1)
- `odin/apps/relays/models.py` (1/1)
- `odin/apps/relays/services.py` (4/4)
- `odin/settings/test.py` (2/0)
- `odin/tests/models/test_relays.py` (84/10)
- `frontend/` (relay indicator icons — see [[2026-09-21-esp8266-indicator-icons]])
- `pyproject.toml` (1/1)
- `uv.lock` (1/1)
- `wiki/.sessions.json` (2/1)
- `wiki/INDEX.md` (1/0)
- `wiki/pages/2026-09-19-mnt-215-midseason-mode.md` (146/0)

## Stat

```text
Makefile                                        |   7 +-

 odin/apps/relays/services.py                    |   8 +-

 odin/tests/models/test_relays.py                |  94 +++++++++++++--

 pyproject.toml                                  |   2 +-

 uv.lock                                         |   2 +-

 wiki/.sessions.json                             |   3 +-

 wiki/INDEX.md                                   |   1 +

 wiki/pages/2026-09-19-mnt-215-midseason-mode.md | 146 ++++++++++++++++++++++++

 8 files changed, 245 insertions(+), 18 deletions(-)
```

## Build plan

## Implementation Plan
### Key Technical Decisions
- Window selection is based on `self.now.hour % 3 == 0`, using the modulus operator against the 24-hour clock.
- The pump runs only inside the active hour during the day: the guard is `self.now.hour >= 6 and self.now.hour % 3 == 0`, so night hours (0–5) never activate midseason heating.
- Servos are always open (OFF) in midseason — the original pump↔servo inversion was removed, since a servo must not close while the pump cycles.
- The `hour % 3` predicate is independent of `minute`, so the existing `get_current_period_from_schedule()` call only matters when the weather branch is skipped.

### Implementation Steps
1. **Update pump midseason branch in `odin/apps/relays/services.py`**: Replace the `8 < outside_temp < 15` block in `RelayTargetStateService.get_pump_target_state` with a new guard based on `self.now.hour >= 6 and self.now.hour % 3 == 0` — returns `(ON, MIDSEASON)` in the active daytime hour, `(OFF, MIDSEASON)` otherwise.
2. **Update servo midseason branch in `odin/apps/relays/services.py`**: In `RelayTargetStateService.get_servo_target_state`, return `(OFF, MIDSEASON)` unconditionally inside the `8 < outside_temp < 15` block — servos stay open for the whole midseason window.

## Refinements

Follow-up changes in the working tree after the initial merge adjust the midseason behavior further:

- **`odin/apps/relays/services.py`** — the pump midseason guard is now
  `self.now.hour >= 6 and self.now.hour % 3 == 0`, so midseason heating never runs at night
  (hours 0–5). The servo midseason branch dropped its hour-based inversion and now returns
  `(OFF, MIDSEASON)` unconditionally — servos always stay open during midseason.
- **`odin/apps/relays/models.py`** — removed `RelayState.IGNORED` from the `RelayState` choices;
  `state` is now `ON`/`OFF`/`UNKNOWN` only. `RelayMode.IGNORED` (used when a servo's related pump
  is off) is kept.
- **Frontend** — the ESP8266 tile now renders relay state/mode via SVG icons and dots instead of
  the old `is_on`-based dots; the `MIDSEASON` mode is surfaced as a tooltip on the indicator. See
  [[2026-09-21-esp8266-indicator-icons]].
- **`odin/tests/models/test_relays.py`** — midseason tests updated to the refined behavior.
- **`odin/settings/test.py`** — `PASSWORD_HASHERS` set to the fast MD5 hasher (test speedup).

## Test Results

- Session status: `resolved`
- OpenCode session id: `ses_f47a82a55ffe6EHsQbDq9UIfPs`
- The midseason tests in `odin/tests/models/test_relays.py` were synced to the refined behavior:
  pump cadence is day-only (`hour >= 6`) and servos stay open at every hour — `58 passed`.
- Test speedup: the slow suite (~82 s) was traced to PBKDF2 password hashing in `UserFactory`
  (≈535 ms per hash, two hashes per API test); `PASSWORD_HASHERS` in `odin/settings/test.py` now
  uses the fast MD5 hasher, dropping the full run to ~4 s.

---

## Follow-ups

- None

## References

- Related: [[2026-09-18-relay-state-mode-refactor]]
- External: https://linear.app/mnt/issue/MNT-215/midseason-mode
