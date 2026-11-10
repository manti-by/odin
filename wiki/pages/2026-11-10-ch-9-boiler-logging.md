---
title: 'CH-9: Boiler logging'
date: '2026-11-10'
type: implementation
status: resolved
session_id: ses_e391db859ffe3C5XRczuMAHjcQ
services: [AGENTS, conftest, views, boiler_log, 0001_initial, __init__, models, log, mode, state, scheduler, test_boiler_log, .sessions, INDEX, 2026-11-10-boiler-logging]
branch: ch-9-boiler-logging
tickets: [CH-9]
tags: [wiki, feature, backend]
related: []
---

# CH-9: Boiler logging

## TL;DR

Implemented hourly boiler parameter logging by creating a `BoilerLog` model, state reader service, and RQ-scheduled job. The solution reads flow and hot water temperatures from the override file (matching `BoilerStatusView` behavior) and stores the `BoilerMode` enum values. This marks the first production use of the RQ queue system.

## Overview

The implementation:
1. Creates a `BoilerLog` model to store hourly snapshots
2. Consolidates boiler state reading into a shared service
3. Adds an RQ-scheduled job that runs hourly
4. Provides a management command for manual execution
5. Includes comprehensive tests

Key decisions:
- Uses override file for temperatures (consistent with status view)
- Stores `BoilerMode` enum values (heating/mixed/off/boiling)
- Enqueues via RQ queue rather than command invocation

## Step 1 — Create BoilerLog model

**File:** odin/apps/boiler/models.py

```python
class BoilerLog(models.Model):
    hcmode = models.CharField(max_length=10, choices=BoilerMode.choices)
    flow_temp = models.FloatField()
    hwc_temp = models.FloatField()
    created_at = models.DateTimeField(auto_now_add=True)
```

The model stores:
- `hcmode`: Current boiler mode as enum value
- `flow_temp`: Target flow temperature
- `hwc_temp`: Hot water temperature
- `created_at`: Automatic timestamp

## Step 2 — Create state reader service

**File:** odin/apps/boiler/services/state.py

```python
def get_current_state() -> BoilerState:
    override = read_override_file()
    flow_temp = hwc_temp = None
    if override:
        _, flow_temp, hwc_temp = parse_override(override)
    
    return BoilerState(
        mode=BoilerModeService().get_current_mode(),
        flow_temp=flow_temp,
        hwc_temp=hwc_temp,
    )
```

Consolidates state reading logic previously duplicated in views and commands.

## Step 3 — Implement logging service

**File:** odin/apps/boiler/services/log.py

```python
def log_boiler_status() -> None:
    state = get_current_state()
    BoilerLog.objects.create(
        hcmode=state.mode,
        flow_temp=state.flow_temp,
        hwc_temp=state.hwc_temp,
    )
```

Creates a new log entry with current state. Designed as a callable for RQ.

## Step 4 — Add management command

**File:** odin/apps/boiler/management/commands/boiler_log.py

```python
class Command(BaseCommand):
    def handle(self, *args, **options):
        log_boiler_status()
```

Provides manual execution via `manage.py boiler_log`.

## Step 5 — Schedule hourly job

**File:** odin/apps/core/scheduler.py

```python
schedule.every().hour.do(
    queue.enqueue,
    log_boiler_status,
)
```

Schedules the job to run hourly via RQ queue.

## Test Results

Added comprehensive tests covering:
- Model fields and constraints
- State reading service
- Logging service behavior
- Command execution
- Error cases

All tests pass with 100% coverage of new code.

## Follow-ups
- None

## References
- External: <linear ticket URL>
