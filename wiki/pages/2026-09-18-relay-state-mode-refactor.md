---
title: Relay state/mode refactor — review, test sync, and fixes
date: 2026-09-18
type: implementation
status: resolved
session_id: ses_relay_state_mode_refactor_2026_09_18
services: [relays, core, dashboard, frontend]
branch: -
tickets: []
tags: [relays, state, mode, review, tests, redis]
related: [2026-09-11-relay-state-redis-consumer, 2026-09-11-add-related-relay-field]
---

# Relay state/mode refactor — review, test sync, and fixes

## TL;DR

Reviewed an uncommitted relay state/mode refactor that moved `Relay.state` out of the JSON `context`
into a dedicated nullable `state`/`mode` column pair (migrations 0007/0008), and changed
`target_state` from a computed tuple to a single value that persists into those columns. The
working tree was broken (29 failing relay tests). After the author fixed the model/service code,
I synced the test suite to the new contract, fixed two real bugs (API update never populated the
`state` column; API reads overwrote the actual state column with the computed target), and added
tests for the inverted pump/servo midseason logic. **All 259 backend tests pass; ruff, Biome, and
`tsc` are clean.**

## Overview

The refactor's intent: make relay state a first-class model field instead of a JSON-context key, so
the dashboard/admin/API can read `state`/`mode` directly. The design also conflates "actual" and
"target" into the same `state` column — a three-way write source (Redis reports via
`refresh_state`, sensor context reports via the update API, and the computed target via
`target_state`). Domain note from the author: **pump and servo states are inverted** — a pump `ON`
means active, a servo `ON` means the circuit is closed (effectively disabled).

Author-confirmed behavior change: in midseason (`8 < outside < 15`) a servo now unconditionally
returns `(ON, MIDSEASON)` outside the first 10 minutes of the hour (previously it fell through to
temperature regulation). This mirrors the pump, which runs `(ON, MIDSEASON)` only in the first 10
minutes — pump and servo are exactly opposite in midseason.

## Step 1 — Sync model tests to the single-value `target_state`

`Relay.target_state` (`odin/apps/relays/models.py:119`) now computes
`RelayTargetStateService(self).get_target_state()`, persists `self.state`/`self.mode`, and returns
only the state. The suite still asserted `(RelayState.X, RelayMode.Y)` tuples.

- **File:** `odin/tests/models/test_relays.py`
- Rewrote every tuple assertion to `assert relay.target_state == RelayState.X` plus
  `assert relay.mode == RelayMode.Y` (the property persists `mode`, so it is observable after the call).
- Servo cases with no sensor / stale sensor / no temp / no target temp now return
  `RelayMode.UNKNOWN` (was `FALLBACK`) — service returns `UNKNOWN` for these.
- `test_relays__servo_stays_open_in_summer` corrected from `IGNORED` to `OFF` (service now returns
  `OFF`).
- Renamed `test_relays__get_relay_data_updates_context` → `test_relays__refresh_state_updates_state`;
  `refresh_state` writes the `state` column, not `context["state"]`.
- Added `test_relays__servo_stays_open_first_ten_minutes_in_midseason` and
  `test_relays__servo_closes_outside_first_ten_minutes_in_midseason` to cover the new inverted
  midseason servo behavior.

## Step 2 — Fix API update to populate the `state` column

`perform_update` merged `context` but never wrote the `state` column, so a relay that only reported
via the API stayed `state=None` forever (the dashboard then showed `is_on=False`).

- **File:** `odin/api/v1/relays/views.py:46`
- When `context` includes a `state`, map it through `RelayState.__members__.get(state, RelayState.UNKNOWN)`
  and add `state` to `update_fields` — matches the test's STANDBY → UNKNOWN expectation.

## Step 3 — Stop API reads from corrupting the actual `state`

The `RelaySerializer.target_state` ChoiceField read `obj.target_state`, which `self.save()`s —
so a plain `GET /api/v1/relays/` overwrote the Redis-reported actual state with the computed
target on every request.

- **File:** `odin/api/v1/relays/serializers.py:13`
- Replaced the field with a `SerializerMethodField` that computes via
  `RelayTargetStateService(obj).get_target_state()` without persisting. Verified the DB column is
  unchanged after serialization.

## Step 4 — Cleanup

- Removed unused `send_push_notification_to_admins` import from
  `odin/apps/core/scheduler.py` (the `update_index_context` cache job it served was removed).
- Removed unused `RelayMode` import from `odin/apps/relays/admin.py`.
- Biome reformat of `frontend/src/components/tile/Esp8266SensorsTile.tsx` (kept the null `mode`
  guard `sensor.relay.mode ? sensor.relay.mode[0] : "-"`).

## Test Results

- `uv run pytest --create-db --disable-warnings --ds=odin.settings.test odin/` → **259 passed**
- `uv run ruff check odin/` → all checks passed
- `uv run ruff format --check odin/` → 178 files already formatted
- `bun run lint` (Biome) → clean; `bun run typecheck` (`tsc -b --noEmit`) → clean

## Known follow-ups

- **Actual-vs-target conflation** — `state` is written by `refresh_state` (actual), API context
  reports (actual), computed `target_state` (target), and admin form edits. The property still
  `self.save()`s when read from admin `save_model`. Consider splitting actual/target into separate
  columns (or compute target without persisting).
- **Dashboard bypasses cache** — `core/views.py:95` now calls `build_index_context()` per request
  (Redis read per relay + `systemctl` subprocess). `get/set_cached_index_context`/
  `update_index_context_cache` are dead in prod, only exercised by `test_context.py`.
- **Admin UX** — `state`/`mode` are editable in the change form, but `save_model` publishes the
  computed `target_state`, not the typed values; admins must use `force_state` to override.
- **Indicator colors** — `Esp8266SensorsTile.tsx:57` maps `is_on ? "cooling" : "heating"`, inverting
  the old mapping; with pump/servo semantics inverted, one color can't represent both — verify intent.
- **`prod.py`** reverts MNT-138 hardening (secure cookies off, `146.120.14.192` dropped from
  `ALLOWED_HOSTS`) — intentional for LAN-over-HTTP, but public-IP requests now get `DisallowedHost`.
- **Frontend types** — `DashboardRelay.state`/`mode` typed `string` but the API returns `null` for
  un-refreshed relays (guarded at runtime, type is technically wrong).
- **`RelayFactory.type = SensorType.ESP8266`** (pre-existing) is an invalid `RelayType`, so
  default-factory relays hit the `case _` UNKNOWN branch.

---

## Follow-ups

- Same as Known follow-ups above; no open blocking issues — working tree is green.

## References

- Related: [[2026-09-11-relay-state-redis-consumer]], [[2026-09-11-add-related-relay-field]]