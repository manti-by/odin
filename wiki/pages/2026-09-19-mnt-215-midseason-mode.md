---
title: 'MNT-215: Midseason mode'
date: '2026-09-19'
type: implementation
status: resolved
session_id: ses_f47a82a55ffe6EHsQbDq9UIfPs
services: [Makefile, services, test_relays, pyproject, uv, .sessions, INDEX, 2026-09-19-mnt-215-midseason-mode]
branch: mnt-215-midseason-mode
tickets: [MNT-215]
tags: [wiki, feature, backend]
related: [2026-09-18-relay-state-mode-refactor]
---
# MNT-215: Midseason mode

## TL;DR

Midseason mode is now activated every 3 hours for 1 hour, replacing the previous 10-minute activation every hour. The update was successfully implemented and all tests have passed. The change is reflected in the updated wiki page and Python files. The new logic uses the modulus operator to determine the activation time.

---

## Overview

The implementation updated the relay state service in `odin/apps/relays/services.py` to enable midseason mode every 3 hours for 1 hour. Key changes include updates to the `get_pump_target_state` and `get_servo_target_state` methods, as well as the addition of a new wiki page `wiki/pages/2026-09-19-mnt-215-midseason-mode.md` and test updates in `odin/tests/models/test_relays.py`.

## Changed files

- `Makefile` (6/1)
- `odin/apps/relays/services.py` (4/4)
- `odin/tests/models/test_relays.py` (84/10)
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
- PUMP and SERVO stay inverted in midseason: pump `ON` ↔ servo `OFF` inside the active hour, pump `OFF` ↔ servo `ON` in the two idle hours.
- The `hour % 3` predicate is independent of `minute`, so the existing `get_current_period_from_schedule()` call only matters when the weather branch is skipped.

### Implementation Steps
1. **Update pump midseason branch in `odin/apps/relays/services.py`**: Replace the `8 < outside_temp < 15` block in `RelayTargetStateService.get_pump_target_state` with a new guard based on `self.now.hour % 3 == 0`.
2. **Update servo midseason branch in `odin/apps/relays/services.py`**: Update the `RelayTarge…

## Test Results

- Session status: `resolved`
- OpenCode session id: `ses_f47a82a55ffe6EHsQbDq9UIfPs`

---

## Follow-ups

- None

## References

- External: https://linear.app/mnt/issue/MNT-215/midseason-mode
