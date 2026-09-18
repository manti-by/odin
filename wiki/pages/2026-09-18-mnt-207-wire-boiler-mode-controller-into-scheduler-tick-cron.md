---
title: 'MNT-207: Wire boiler mode controller into scheduler tick / cron'
date: '2026-09-18'
type: implementation
status: resolved
session_id: ses_f4b5201d1ffecEL0NTp7C5FSiC
services: [__init__, controller, mode, scheduler, test_boiler_mode_controller, pyproject,
  uv]
branch: mnt-207-wire-boiler-mode-controller-into-scheduler-tick-cron
tickets: [MNT-207]
tags: [wiki, backend, feature]
related: []
---
# MNT-207: Wire boiler mode controller into scheduler tick / cron

## TL;DR

The boiler mode controller is now invoked periodically via a scheduler, ensuring the boiler reacts to changes within minutes. A new dedicated cron job was created with a 5-minute interval, and a thin wrapper function was added for testability. The implementation respects the weekly boiling override and is DST-safe.

---

## Overview

The implementation involved creating a new `BoilerModeController` class in `odin/apps/boiler/services/controller.py` and registering a scheduled job in `odin/apps/core/scheduler.py`. The `BoilerModeController` is invoked every 5 minutes, and the implementation includes a thin wrapper function `run_boiler_mode_controller` for testability. Key files modified include `odin/apps/boiler/services/__init__.py`, `odin/apps/core/scheduler.py`, and `odin/tests/services/test_boiler_mode_controller.py`.

## Changed files

- `odin/apps/boiler/services/__init__.py` (10/0)
- `odin/apps/boiler/services/controller.py` (61/0)
- `odin/apps/boiler/services/mode.py` (8/4)
- `odin/apps/core/scheduler.py` (29/0)
- `odin/tests/services/test_boiler_mode_controller.py` (104/0)
- `pyproject.toml` (1/1)
- `uv.lock` (1/1)

## Stat

```text
odin/apps/boiler/services/__init__.py              |  10 ++

 odin/apps/boiler/services/controller.py            |  61 ++++++++++++

 odin/apps/boiler/services/mode.py                  |  12 ++-

 odin/apps/core/scheduler.py                        |  29 ++++++

 odin/tests/services/test_boiler_mode_controller.py | 104 +++++++++++++++++++++

 pyproject.toml                                     |   2 +-

 uv.lock                                            |   2 +-

 7 files changed, 214 insertions(+), 6 deletions(-)
```

## Build plan

## Implementation Plan
### Background
The implementation plan for MNT-207 involves creating a periodic invocation of the `BoilerModeController` service. Since the `update_index_context` job does not exist in `odin/apps/core/scheduler.py`, a new dedicated cron job will be created.

### Key Technical Decisions
- **Interval Trigger**: A 5-minute interval trigger will be used, which is DST-safe by construction.
- **APScheduler Configuration**: The scheduler will be configured with `max_instances=1` and `replace_existing=True` to ensure an overlap-free single flight and to propagate code changes after a `scheduler.service` restart.
- **Code Organization**: The new code will be kept in a sibling service module `odin/apps/boiler/services/controller.py`.
- **Boiler Mode Mapping**: The `BoilerMode` decision returns `HEATING` when the outside temperature is 15°C or higher
  or all pumps are off, otherwise `MIXED` (including missing weather); an active water override yields `None` to skip.

## Test Results

- Session status: `resolved`
- OpenCode session id: `ses_f4b5201d1ffecEL0NTp7C5FSiC`

---

## Follow-ups

- None

## References

- External: https://linear.app/mnt/issue/MNT-207/wire-boiler-mode-controller-into-scheduler-tick-cron
