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
related: []
---
# MNT-206: Boiler mode controller

## TL;DR

The BoilerModeController service was implemented to map pump/servo and weather states to BoilerService, enabling automated boiler mode control. The service reads aggregated states, decides the boiler mode based on heating rules, and applies it via BoilerService. The implementation includes unit tests and handles DST and unknown relay states.

---

## Overview

The BoilerModeController service was added to odin/apps/boiler/services.py, which reads aggregated pump/servo target states via RelayTargetStateService and weather temperature bands, and calls the appropriate BoilerService method. The implementation includes a decision matrix and handles edge cases, with unit tests covered in odin/tests/services/test_boiler_mode_controller.py.

## Changed files

- `odin/apps/boiler/services.py` (120/0)
- `odin/tests/services/test_boiler_mode_controller.py` (256/0)
- `pyproject.toml` (1/1)
- `uv.lock` (2/2)

## Stat

```text
odin/apps/boiler/services.py                       | 120 ++++++++++

 odin/tests/services/test_boiler_mode_controller.py | 256 +++++++++++++++++++++

 pyproject.toml                                     |   2 +-

 uv.lock                                            |   4 +-

 4 files changed, 379 insertions(+), 3 deletions(-)
```

## Build plan

## Implementation Plan
The implementation plan for the BoilerModeController service is as follows:

### Key Technical Decisions
- The service will be implemented as a synchronous service, invoked from the scheduler.
- The service will read aggregated pump/servo target states via RelayTargetStateService and weather temperature bands.
- The service will call the appropriate BoilerService method based on the decision matrix.
- The service will handle DST and unknown relay states gracefully.

### Implementation Steps
1. Create a new class `BoilerModeController` in `odin/apps/boiler/services.py`.
2. Define the service contract, including the `run` method that decides the mode and applies it via BoilerService.
3. Implement the decision matrix, including the logic for handling different temperatu…

## Test Results

- Session status: `resolved`
- OpenCode session id: `ses_f5078b891ffedDduGWfPH224I5`

---

## Follow-ups

- None

## References

- External: https://linear.app/mnt/issue/MNT-206/boiler-mode-controller
