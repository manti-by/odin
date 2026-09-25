---
title: SensorLog and Sensor Relay FK Migrations
date: 2026-09-24
type: implementation
status: resolved
session_id: ses_f2dd2e2e6ffeugjpnpEXzSIr36
services: [sensors, api]
branch: -
tickets: []
tags: [sensors, telemetry, django, migrations]
related: [2026-07-16-sensor-model-queryset-manager]
---

# SensorLog and Sensor Relay FK Migrations

## TL;DR

Replaced the string-based relation columns used by sensor telemetry and relay control with nullable FKs:
`SensorLog.sensor` now points to `Sensor`, and `Sensor.relay` now points to `Relay`.
Migrations `0016` and `0017` preserve legacy identifiers, backfill existing rows in batches, and leave unmatched
values in the legacy columns. The public telemetry/Redis contracts and nested dashboard response remain unchanged;
all 365 tests pass.

---

## Overview

`SensorLog.sensor_id` was a free-form string with no referential integrity, so logs
could drift from `Sensor` rows. The FK points at the `Sensor` PK (not `sensor_id`,
which is not unique), and the old column is preserved as `sensor_id_old` for
traceability and orphan display.

## Step 1 — Model change

**File:** `odin/apps/sensors/models.py:139`

- `SensorLogManager.current()` now filters `sensor__is_active=True` with
  `DISTINCT ON (sensor)` instead of matching char `sensor_id` strings.
- `Sensor.latest_log` filters `sensor=self` instead of `sensor_id=self.sensor_id`.
- New `sensor_id_value` property resolves the display id from the FK or the legacy
  column; `__str__` uses it.

## Step 2 — Data migration

**File:** `odin/apps/sensors/migrations/0016_sensorlog_sensor_fk.py`

- `RenameField sensor_id → sensor_id_old` (old relations intact, no column drop).
- Alter `sensor_id_old` to nullable, then `AddField sensor` FK (new `sensor_id`
  integer column, `SET_NULL`).
- `RunPython` builds a `{sensor_id_string: pk}` map ordered by `created_at, id`
  (latest wins on duplicate strings) and `bulk_update`s logs in batches of 1000;
  unmapped logs keep `sensor=NULL`. Reverse is a noop since old values are kept.

## Step 3 — Dependents rewired, API contract preserved

- **File:** `odin/api/v1/sensors/serializers.py:37` — `SensorLogSerializer` still
  accepts/returns `sensor_id` as a string; `create()` looks up the `Sensor`
  (unknown → `sensor=None`, raw string kept in `sensor_id_old`).
- **File:** `odin/api/v1/sensors/views.py:60` — `perform_create` delegates to
  `serializer.save()`; list queryset adds `select_related("sensor")`.
- **File:** `odin/apps/sensors/services.py:16` — chart aggregation resolves the id
  via `log.sensor` / `sensor_id_old` and filters `sensor__sensor_id__in`.
- **File:** `odin/apps/core/management/commands/consumer.py:128` — Redis consumer
  stores both `sensor` and `sensor_id_old`.
- **File:** `odin/apps/sensors/admin.py:23` — list/search/filter on the relation.
- **File:** `odin/tests/factories.py:71` — `SensorLogFactory(sensor=...)`; all
  call sites switched from `sensor_id=x.sensor_id` (dashboard tests now capture
  the `Sensor` object instead of reusing literal strings).

## Test Results

- `uv run pytest --create-db --disable-warnings --ds=odin.settings.test odin/` —
  **365 passed**.
- `makemigrations --dry-run --check`, `ruff check`, `ruff format --check`,
  `ty check` — all clean (one `# ty: ignore` kept for the FK descriptor access,
  matching existing convention in `views.py`).

---

## Update — 2026-09-24 22:55

The relay relation was migrated in the same way as `SensorLog.sensor`.

### Sensor-to-relay FK

**Files:** `odin/apps/sensors/models.py`, `odin/apps/relays/models.py`

- `Sensor.relay` is now a nullable FK to `relays.Relay` with `on_delete=models.SET_NULL` and
  `related_name="sensors"`.
- The old string column is retained as `relay_id_old`; the new FK's implicit `relay_id` is an integer PK.
- Removed the string-based `Sensor.relay` lookup.
- `Relay.sensor` now filters through `relay=self`, returns the most recently created linked sensor with a
  deterministic `created_at, id` tie-breaker, and returns `None` for unsaved relays.
- The dashboard uses `select_related("relay")`; the nested response still exposes the Relay business key as a
  string.

### Relay data migration

**File:** `odin/apps/sensors/migrations/0017_sensor_relay_fk.py`

- Renames the legacy `Sensor.relay_id` column to `relay_id_old`.
- Adds the nullable `Sensor.relay` FK with `SET_NULL` and `related_name="sensors"`.
- Temporarily removes and recreates the legacy column index to avoid a generated index-name collision with the
  new FK index on PostgreSQL.
- Runs a batched data migration that maps each `relay_id_old` to the latest `Relay.pk` with the same business
  ID. Empty, null, and unmatched values leave `relay=NULL` while preserving the legacy value.
- Depends on both `sensors.0016_sensorlog_sensor_fk` and the latest Relay migration; `0016` and `0017` should be
  deployed together when neither has been applied.

### Dependents and validation

- Updated the Sensor admin, dashboard, factories, and relay/model/API tests to use `relay=relay_instance`.
- Relay deletion now sets `Sensor.relay` to `NULL` and leaves `relay_id_old` intact.
- The Redis `relay_id` contract, Relay API URLs, and frontend payload shape remain unchanged.
- `uv run pytest --create-db --disable-warnings --ds=odin.settings.test odin/` — **365 passed**.
- `makemigrations --dry-run --check`, `ruff check`, `ruff format --check`, and `ty check` are clean.
- Manual MigrationExecutor checks on SQLite and PostgreSQL confirmed matched and unmatched legacy IDs are migrated
  without losing `relay_id_old`.

---

## Follow-ups

- None. Optional later cleanup: drop `sensor_id_old` and `relay_id_old` after unmatched legacy values have been
  reconciled (requires follow-up migrations and serializer/admin touch-ups).

## References

- Related: [[2026-07-16-sensor-model-queryset-manager]]
