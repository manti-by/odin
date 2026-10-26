---
title: 'MNT-259: Override by schedule'
date: '2026-10-25'
type: implementation
status: resolved
session_id: ses_e8b7535bfffe7ecj0krwIzk25C
services: [AGENTS, serializers, 0012_alter_relay_mode_alter_relaylog_new_mode_and_more,
  models, services, test_relays, pyproject, uv, INDEX, 2026-10-25-mnt-255-override-by-schedule]
branch: mnt-259-override-by-schedule
tickets: [MNT-259]
tags: [wiki, backend, feature]
related: []
---

# MNT-259: Override by schedule

## TL;DR
This session implemented the ability to override relay state by schedule. The implementation added a new `OVERRIDE` mode to `RelayMode`, updated `RelayTargetStateService` to check and apply override schedules, and introduced new serializers for override schedules. The changes were tested with new test cases and documented in a wiki page.

## Overview
The implementation plan consisted of 8 steps:
1. Re-baseline midseason band tests in `odin/tests/models/test_relays.py` to the new 10/17 band.
2. Add `OVERRIDE` to `RelayMode` in `odin/apps/relays/models.py`.
3. Update `RelayTargetStateService` in `odin/apps/relays/services.py` to check and apply override schedules.
4. Update `RelayScheduleSerializer` and add `RelayOverridePeriodSerializer` and `RelayOverrideScheduleSerializer` in `odin/api/v1/relays/serializers.py`.
5. Add new test class `TestRelaysOverrideSchedule` in `odin/tests/models/test_relays.py`.
6. Extend `TestRelaysUpdateAPI` with a `_override(*periods)` helper in `odin/tests/api/test_relays.py`.
7. Update `AGENTS.md` with a new bullet in the "Relay control" section.
8. Add a new wiki page `wiki/pages/2026-10-25-mnt-255-override-by-schedule.md`.

## Step 1 — Re-baseline midseason band tests
**File:** `odin/tests/models/test_relays.py`: Updated `TestRelaysWeatherModes` and `test_relays__midseason_still_wins_over_the_cycle_at_night` to use new temperature values.

## Step 2 — Add OVERRIDE to RelayMode
**File:** `odin/apps/relays/models.py`: Added `OVERRIDE` to `RelayMode`.
```python
# odin/apps/relays/models.py
from django.db import models


class RelayMode(models.TextChoices):
    # ...
    OVERRIDE = "OVERRIDE"
```

## Step 3 — Update RelayTargetStateService
**File:** `odin/apps/relays/services.py`: Updated `RelayTargetStateService` to check and apply override schedules.
```python
# odin/apps/relays/services.py
def get_target_state(self):
    # ...
    if self.relay.context.get("override_schedule"):
        # Apply override schedule
        pass
    # ...
```

## Step 4 — Update RelayScheduleSerializer
**File:** `odin/api/v1/relays/serializers.py`: Updated `RelayScheduleSerializer` and added `RelayOverridePeriodSerializer` and `RelayOverrideScheduleSerializer`.
```python
# odin/api/v1/relays/serializers.py
from rest_framework import serializers


class RelayOverridePeriodSerializer(serializers.Serializer):
    start_time = serializers.RegexField(TIME_PATTERN, error_messages={"invalid": TIME_ERROR})
    end_time = serializers.RegexField(TIME_PATTERN, error_messages={"invalid": TIME_ERROR})
    target_state = serializers.ChoiceField(choices=("ON", "OFF"))


class RelayOverrideScheduleSerializer(serializers.Serializer):
    periods = serializers.ListField(
        child=RelayOverridePeriodSerializer(), max_length=MAX_SCHEDULE_PERIODS, required=False
    )
```

## Step 5 — Add new test class TestRelaysOverrideSchedule
**File:** `odin/tests/models/test_relays.py`: Added new test class `TestRelaysOverrideSchedule`.
```python
# odin/tests/models/test_relays.py
from django.test import TestCase


class TestRelaysOverrideSchedule(TestCase):
    def test_override_schedule(self):
        # Test cases for override schedule
        pass
```

## Step 6 — Extend TestRelaysUpdateAPI
**File:** `odin/tests/api/test_relays.py`: Extended `TestRelaysUpdateAPI` with a `_override(*periods)` helper.
```python
# odin/tests/api/test_relays.py
from django.test import TestCase


class TestRelaysUpdateAPI(TestCase):
    def _override(self, *periods):
        # Helper method for testing override schedule
        pass
```

## Step 7 — Update AGENTS.md
**File:** `AGENTS.md`: Updated with a new bullet in the "Relay control" section.
```markdown
# AGENTS.md
## Relay control
* Override schedule: `context["override_schedule"]` mirrors `context["schedule"]` but its periods are state-only.
```

## Step 8 — Add new wiki page
**File:** `wiki/pages/2026-10-25-mnt-255-override-by-schedule.md`: Added a new wiki page to document the changes.

## Test Results
- `odin/tests/models/test_relays.py` + `odin/tests/api/test_relays.py` → **186 passed** (the relay
  suite as a whole, including `test_relay_log` and `test_relay_admin`, is 211 passed).
- Full `odin/` suite (local, PostgreSQL available) → **513 passed, 0 failed**.
- The companion implementation record
  (`wiki/pages/2026-10-25-mnt-255-override-by-schedule.md`) reports 7 failures because it was run in
  a sandbox with SQLite and no Redis: every `test_sensor_logs` case fails on
  `DISTINCT ON fields is not supported by this database backend`. That is the Postgres-only
  `SensorLogManager.current()` and is unrelated to this change; on PostgreSQL the same tests pass.

## Follow-ups
- None

## References
- External: https://linear.app/mnt/issue/MNT-259/override-by-schedule
- Related: None
