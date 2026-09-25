---
title: 'MNT-206: Boiler mode controller'
date: '2026-09-17'
type: implementation
status: resolved
session_id: ses_f5078b891ffedDduGWfPH224I5
services: [services, test_boiler_mode_controller, pyproject, uv]
branch: mnt-206-boiler-mode-controller
tickets: [MNT-206]
tags: [wiki, backend, feature]
related: [2026-09-18-mnt-207-wire-boiler-mode-controller-into-scheduler-tick-cron]
---
# MNT-206: Boiler mode controller

## TL;DR

The BoilerModeService decision service was implemented in `odin/apps/boiler/services/mode.py` to map aggregated pump
target states and outside temperature onto a BoilerMode. Styled after RelayTargetStateService, it is a pure decision
service: `get_target_mode()` returns a mode (or None when a boiling override owns the boiler) and leaves applying it
to the caller. The monolithic `odin/apps/boiler/services.py` was split into the `odin/apps/boiler/services/` package,
with `BoilerService` renamed to `BoilerStatusService`.

---

## Overview

The monolithic `odin/apps/boiler/services.py` (with `BoilerService`) was split into the `odin/apps/boiler/services/`
package: `ebusd.py` (bus client), `status.py` (`BoilerStatusService`, formerly `BoilerService`), and `mode.py`
(`BoilerMode` + `BoilerModeService`). The `boiler_set`/`boiler_status` management commands were updated to the new
import paths. `BoilerModeService` aggregates the target state of every active pump through RelayTargetStateService and
maps it plus the outside temperature onto a boiler mode, following the RelayTargetStateService code style (public
methods only, flat early returns, `__init__` preloading `Weather.objects.current()`).

Decision matrix (`t` is the current outside temperature, °C):

- active boiling override (`water` mode in `BoilerStatusService.current_override()`) -> None: leave the boiler
  untouched so the scheduled hot-water cycle is never fought;
- no weather or temperature available -> `MIXED` (fail-safe keeps both circuits fed);
- `t >= 15` (summer) -> `HEATING`;
- aggregated pump state OFF -> `HEATING`;
- otherwise -> `MIXED`.

Pump aggregation (`get_pumps_state`): no active pumps -> UNKNOWN; all pumps OFF -> OFF; any pump ON -> ON. Servo states
are no longer consulted, and `BoilerMode.OFF` / `BoilerMode.CLEAR_OVERRIDE` are currently unreturned.

## Changed files

- `odin/apps/boiler/services.py` (deleted, 327 lines split into the package below)
- `odin/apps/boiler/services/__init__.py` (new, 16 lines)
- `odin/apps/boiler/services/ebusd.py` (new, 55 lines)
- `odin/apps/boiler/services/mode.py` (new, 49 lines)
- `odin/apps/boiler/services/status.py` (new, 162 lines)
- `odin/apps/boiler/management/commands/boiler_set.py` (import path + `BoilerStatusService` rename)
- `odin/apps/boiler/management/commands/boiler_status.py` (import path + `BoilerStatusService` rename)
- `odin/tests/services/test_boiler_mode_controller.py` (import paths updated to `services.mode` / `services.status`)

## Stat

```text
odin/apps/boiler/services.py                       | 327 ---------------------
odin/apps/boiler/services/__init__.py              |  16 +++
odin/apps/boiler/services/ebusd.py                 |  55 +++
odin/apps/boiler/services/mode.py                  |  49 +++
odin/apps/boiler/services/status.py                | 162 +++
odin/apps/boiler/management/commands/boiler_set.py |   5 +-
odin/apps/boiler/management/commands/boiler_status.py |   6 +-
odin/tests/services/test_boiler_mode_controller.py |   6 +-
```

## Build plan

## Implementation Plan
The implementation plan for the BoilerModeService is as follows:

### Key Technical Decisions
- The monolithic boiler `services.py` is split into a package (`ebusd` / `status` / `mode`); `BoilerService` is renamed
  to `BoilerStatusService` to reflect that it owns bus I/O and override state.
- The mode service is a pure decision service styled after RelayTargetStateService: no private methods, flat early
  returns, main entry point `get_target_mode()` returning `BoilerMode | None`. Applying the mode stays with the caller.
- Only pump target states feed the decision; an active `water` override always wins (returns None).
- Missing weather/temperature fails safe to `MIXED` instead of skipping.

### Implementation Steps
1. Split `odin/apps/boiler/services.py` into `odin/apps/boiler/services/` (`__init__.py`, `ebusd.py`, `status.py`,
   `mode.py`) and rename `BoilerService` to `BoilerStatusService`.
2. Implement `BoilerModeService` with `get_pumps_state()` (pump aggregation) and `get_target_mode()` (decision matrix
   above) in `odin/apps/boiler/services/mode.py`.
3. Update the `boiler_set` / `boiler_status` commands and test imports to the new paths.

## Test Results

- Session status: `resolved`
- OpenCode session id: `ses_f5078b891ffedDduGWfPH224I5`

---

## Follow-ups

- `odin/tests/services/test_boiler_mode_controller.py` still imports `BoilerModeController` (and the removed
  `DEFAULT_*` constants), so it fails at collection; it needs rewriting against `BoilerModeService.get_target_mode()`.
- Decide whether the currently unreturned `BoilerMode.OFF` / `BoilerMode.CLEAR_OVERRIDE` members stay for future use or
  should be removed.

> **Note 2026-09-25 (Consistency Agent):** both follow-ups are resolved in the current tree. The test
> imports `BoilerModeService`/`BoilerMode` from `odin/apps/boiler/services/mode.py` and exercises
> `get_target_mode()`. The apply half was added later as `odin/apps/boiler/services/controller.py`
> (see [[2026-09-18-mnt-207-wire-boiler-mode-controller-into-scheduler-tick-cron]]), which consumes
> `BoilerMode.OFF`/`CLEAR_OVERRIDE`.

## References

- External: https://linear.app/mnt/issue/MNT-206/boiler-mode-controller
