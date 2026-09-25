---
title: Relay mode computed on read
date: 2026-09-23
type: implementation
status: resolved
session_id: ses_f36363e46ffe9xrDG6f28XcHL8
services: [api, relays]
branch: -
tickets: []
tags: [relays, mode, api, dashboard, serializers]
related:
  - 2026-09-19-mnt-215-midseason-mode
  - 2026-09-18-relay-state-mode-refactor
  - 2026-09-21-esp8266-indicator-icons
  - 2026-09-23-mnt-218-split-dashboard-api
---

# Relay mode computed on read

## TL;DR

`SERVO-BR` and `SERVO-HL` showed different modes on the dashboard although both are
related to the same pump and share the same inputs. The cause was that `Relay.mode` is a
persisted snapshot written only on admin/API saves, and both the dashboard serializer and
the CRUD serializer served that stale column. Fix: compute `mode` (and `target_state`) on
read via a new non-persisting `Relay.get_target_state()`, so every API response reflects the
live target decision.

---

## Overview

The two servos looked different because they *were* different in the database — but only in
the stored `mode` column, not in the live computation. Diagnosing with the real service showed
both compute to the same mode; one had simply not been recomputed since the pump's stored
state changed.

Evidence (live DB, before the fix):

```
PUMP-WF-1 stored state = OFF, computed now = (OFF, MIDSEASON)
SERVO-BR  stored mode = MIDSEASON | computed now = (OFF, IGNORED)   <-- stale
SERVO-HL  stored mode = IGNORED   | computed now = (OFF, IGNORED)   <-- current
```

`mode` was written at these timestamps (10 ms apart, with the pump's stored state flipping
between the two writes):

```
SERVO-HL  mode=IGNORED    updated 2026-09-21 13:16:08.856301+00:00
SERVO-BR  mode=MIDSEASON  updated 2026-09-21 13:16:08.866774+00:00
```

`mode` is only recomputed by `RelayAdmin.save_model` (`odin/apps/relays/admin.py:128`) and
`RelayRetrieveUpdateView.perform_update` (`odin/api/v1/relays/views.py:66`). There is no
scheduled recompute — `odin/apps/core/scheduler.py` only runs weather/voltage/rates/traffic —
and `Relay.refresh_state()` updates `state` only, never `mode`. The frontend tile switches on
`relay.mode` (`frontend/src/components/tile/Esp8266SensorsTile.tsx:25`), so the stale value was
what users saw.

## Step 1 — Extract a non-persisting target computation

**File:** `odin/apps/relays/models.py:118`

The `target_state` property both computes and saves. Added `get_target_state()` that delegates
to `RelayTargetStateService` without writing, and reused it from the property so there is a
single call site.

```python
@property
def target_state(self) -> RelayState:
    self.state, self.mode = self.get_target_state()
    self.save()

    return self.state


def get_target_state(self) -> tuple[RelayState, RelayMode]:
    """Compute the target state and mode without persisting them."""
    from odin.apps.relays.services import RelayTargetStateService

    return RelayTargetStateService(self).get_target_state()
```

## Step 2 — Compute mode on read in the CRUD API

**File:** `odin/api/v1/relays/serializers.py:40`

`RelaySerializer` previously declared `mode` as a stored `CharField` and `target_state` as a
`SerializerMethodField` that re-ran the service. Replaced both with a single
`to_representation` override that computes the tuple once per object.

```python
class RelaySerializer(BaseSerializer):
    relay_id = serializers.CharField()
    name = serializers.CharField()
    type = serializers.CharField()
    state = serializers.CharField()
    context = serializers.JSONField()
    created_at = serializers.DateTimeField(read_only=True)

    def to_representation(self, instance: Relay) -> dict:
        data = super().to_representation(instance)
        state, mode = instance.get_target_state()
        data["mode"] = str(mode)
        data["target_state"] = str(state)
        return data
```

`state` stays the persisted physical state; only `mode`/`target_state` are computed.

## Step 3 — Compute mode on read in the dashboard

**File:** `odin/api/v1/core/serializers.py:47`

> **Note 2026-09-25 (Consistency Agent):** `DashboardRelaySerializer` now lives in
> `odin/api/v1/sensors/serializers.py`. It moved when MNT-218 split the dashboard API and removed
> the aggregate `core/dashboard/` endpoint (see [[2026-09-23-mnt-218-split-dashboard-api]]); the
> serializer shape described below is unchanged.

This is the path the SPA tile actually reads (`DashboardSensorSerializer.get_relay`). Its
`mode` field became a `SerializerMethodField` backed by the same helper.

```python
class DashboardRelaySerializer(serializers.Serializer):
    relay_id = serializers.CharField(max_length=32)
    name = serializers.CharField(max_length=32)
    type = serializers.CharField(max_length=32)
    state = serializers.CharField(max_length=32)
    mode = serializers.SerializerMethodField()
    is_on = serializers.BooleanField()

    def get_mode(self, obj: Any) -> str:
        _, mode = obj.get_target_state()
        return str(mode)
```

## Test Results

- `odin/tests/api/test_relays.py::test_relays__retrieve_computes_mode_on_read` — servo with
  stored `MIDSEASON` and an OFF related pump returns `IGNORED`.
- `odin/tests/views/test_dashboard.py::test_dashboard__relay_mode_computed_on_read` — same
  scenario through `DashboardRelaySerializer`.
- `ruff check`, `ruff format --check`, `ty check`, `pre-commit`, and the full suite are green:
  `327 passed`.
- Post-fix, both serializers agree for both servos (live DB, read-only):

```
SERVO-BR  stored mode=MIDSEASON | RelaySerializer=MIDSEASON | Dashboard=MIDSEASON
SERVO-HL  stored mode=IGNORED   | RelaySerializer=MIDSEASON | Dashboard=MIDSEASON
```

---

## Follow-ups

- The persisted `mode` column still drifts: it is written on admin/API saves only, and no
  scheduled job recomputes it. The API now ignores it on read, so this is cosmetic in the DB.
  If the stored column should stay accurate, add a periodic recompute (e.g. APScheduler calling
  `target_state` for active relays).
- `related_relay.is_on` reads the pump's stored `state`, which is itself refreshed only on
  admin/consumer/dashboard paths. Servo modes are consistent with each other, but the pump
  state feeding them can lag.

## References

- Related: [[2026-09-19-mnt-215-midseason-mode]]
- Related: [[2026-09-18-relay-state-mode-refactor]]
- Related: [[2026-09-21-esp8266-indicator-icons]]
