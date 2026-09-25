---
title: Sensor relation FKs and denormalized readings
date: 2026-09-24
type: implementation
status: resolved
session_id: ses_f2dd2e2e6ffeugjpnpEXzSIr36
services: [sensors, relays, api]
branch: -
tickets: []
tags: [sensors, relays, telemetry, django, migrations, denormalization]
related: [2026-07-16-sensor-model-queryset-manager]
---

# Sensor relation FKs and denormalized readings

## TL;DR

Sensor telemetry and relay/linked relations moved from free-form char columns to nullable FKs
(`SensorLog.sensor` → `Sensor`, `Sensor.relay` → `Relay`, `Sensor.linked_sensor` → `Sensor`), the
legacy `*_old` columns were dropped, and the current `temp`/`humidity` readings are now cached on
`Sensor` instead of derived per-read from the latest `SensorLog`. `is_alive` reflects the last ingest
(`Sensor.updated_at`). Migrations `0016`–`0022`; 367 tests pass; the API payload shape (string
`sensor_id`/`relay_id`, offset-applied temperatures) is unchanged.

---

## Overview

`SensorLog.sensor_id` was a free-form string with no referential integrity, so logs could drift from
`Sensor` rows. The FK points at the `Sensor` PK (not `sensor_id`, which is not unique), and the old
column was kept as `sensor_id_old` during the transition before being dropped in `0018`.

The same treatment was applied to `Sensor.relay_id` and `Sensor.linked_sensor_id` (`0017`, `0020`).
`Sensor.temp`/`Sensor.humidity` then became denormalized caches of the latest ingest so read paths no
longer query `SensorLog` for the current value (`0019`, `0022`).

## Step 1 — SensorLog.sensor FK

**File:** `odin/apps/sensors/models.py`

- `SensorLogManager.current()` filters `sensor__is_active=True` with `DISTINCT ON (sensor)` instead
  of matching char `sensor_id` strings.
- `__str__` resolves the display id via the FK (`self.sensor.sensor_id`), falling back to `"unknown"`.

**File:** `odin/apps/sensors/migrations/0016_sensorlog_sensor_fk.py`

- `RenameField sensor_id → sensor_id_old` (old relations intact, no column drop).
- Alter `sensor_id_old` to nullable, then `AddField sensor` FK (`SET_NULL`).
- `RunPython` builds a `{sensor_id_string: pk}` map ordered by `created_at, id` (latest wins on
  duplicate strings) and `bulk_update`s logs in batches of 1000; unmapped logs keep `sensor=NULL`.

Historical note: the `Sensor.latest_log` accessor and `sensor_id_value` property described in this
page's first revision were superseded by the denormalized fields and removed (see the 2026-09-25
update).

## Step 2 — Dependents rewired, API contract preserved

- **File:** `odin/api/v1/sensors/serializers.py` — `SensorLogSerializer` still accepts/returns
  `sensor_id` as a string; `create()` looks up the `Sensor` (unknown → `sensor=None`).
- **File:** `odin/api/v1/sensors/views.py` — `perform_create` delegates to `serializer.save()`; the
  list queryset adds `select_related("sensor")`.
- **File:** `odin/apps/sensors/services.py` — chart aggregation filters `sensor__sensor_id__in` and
  resolves the id via `log.sensor`.
- **File:** `odin/apps/core/management/commands/consumer.py` — the Redis consumer stores `sensor`.
- **File:** `odin/apps/sensors/admin.py` — list/search/filter on the relation.

## Step 3 — Sensor.relay FK

**Files:** `odin/apps/sensors/models.py`, `odin/apps/relays/models.py`,
`odin/apps/sensors/migrations/0017_sensor_relay_fk.py`

- `Sensor.relay` is a nullable FK to `relays.Relay` (`SET_NULL`, `related_name="sensors"`).
- `Relay.sensor` reads through `related_name="sensors"`, ordering by `-created_at`, and returns `None`
  when no sensor is linked.
- The batched data migration maps each `relay_id_old` to the latest `Relay.pk` with the same business
  ID; empty, null, and unmatched values leave `relay=NULL`.
- The migration temporarily drops the legacy column index to avoid an index-name collision with the
  new FK index on PostgreSQL.

## Test Results (initial FK migration)

- `uv run pytest --create-db --disable-warnings --ds=odin.settings.test odin/` — **365 passed**.
- `makemigrations --dry-run --check`, `ruff check`, `ruff format --check`, `ty check` — clean.

---

## Update — 2026-09-25

Legacy columns dropped, `linked_sensor` moved to an FK, and current readings denormalized onto
`Sensor`. This continues the same refactor; it is not a separate change.

### Legacy columns and linked sensor FK

- `0018_remove_sensor_relay_id_old_and_more.py` drops `Sensor.relay_id_old` and
  `SensorLog.sensor_id_old` once the backfill is complete.
- `0020_sensor_linked_sensor_fk.py` renames `Sensor.linked_sensor_id` to `linked_sensor_id_old`, adds
  the nullable self-FK `Sensor.linked_sensor` (`SET_NULL`, `related_name="linked_sensors"`), and
  backfills it in batches; `0021_remove_sensor_linked_sensor_id_old.py` drops the legacy column.

### Denormalized readings

**Files:** `odin/apps/sensors/models.py`,
`odin/apps/sensors/migrations/0019_sensor_humidity_sensor_temp.py`

- `Sensor.temp` and `Sensor.humidity` are stored fields; `0019` adds them (temp defaulted to `0.0`)
  and `0022_alter_sensor_temp.py` makes `temp` nullable so "no reading" is representable.
- `Sensor.update(temp, humidity)` stores the calibrated value (`raw + temp_offset` /
  `humidity_offset`, matching the previous read-time property), skips only genuinely missing values
  (`is not None`, so a real `0` is recorded), bumps `updated_at`, and returns whether anything changed.
- `is_alive` compares `Sensor.updated_at` (last ingest) against the 10-minute threshold instead of the
  latest log's `created_at`.

### Ingest and dependents

- **File:** `odin/apps/core/management/commands/consumer.py` — calls
  `sensor.update(temp=…, humidity=…)` for a matching sensor before persisting the `SensorLog`.
- **File:** `odin/api/v1/sensors/serializers.py` — `SensorLogSerializer.create()` does the same lookup
  and update; `SensorSerializer.temp`/`humidity` declare `allow_null`.
- **File:** `odin/apps/sensors/admin.py` — `temp`, `humidity`, `updated_at`, `created_at` are readonly.

### Bugs fixed while finishing the refactor

- `odin/apps/sensors/services.py` chart aggregation filtered `SensorLog` by `sensor_id__in=<strings>`
  against the integer FK (`operator does not exist: bigint = character varying`); now
  `sensor__sensor_id__in`.
- `consumer.py` called `sensor.update(tempt=…)` (typo) and passed the removed `updated_at` argument.
- `Sensor.update()` wrote `self.created_at` while listing `updated_at` in `update_fields`, and used
  truthiness checks that silently dropped a genuine `0`.

### Test updates

- **File:** `odin/tests/factories.py` — `SensorLogFactory._create` mirrors the ingest pipeline by
  calling `sensor.update(...)`, so creating a log implies the sensor's cached reading.
- The two liveness tests backdate `Sensor.updated_at`; `is_alive` is sensor-level now, not log-level.
- The consumer test creates the matching `Sensor` and asserts its cached temp/humidity, which would
  have caught the `tempt` typo.

### Test Results

- `uv run pytest --create-db --disable-warnings odin/` — **367 passed**.
- `makemigrations --dry-run --check`, `manage.py check --fail-level WARNING`, `ruff check`,
  `ruff format --check`, `ty check`, `bandit` — clean.

---

## Follow-ups

- `0022` only makes `temp` nullable; it does not backfill `Sensor.temp`/`humidity` from the latest
  `SensorLog`. Existing PostgreSQL rows keep `NULL` until the next ingest. A one-off data migration can
  seed them from `SensorLogManager.current()` if that gap matters.
- `Sensor.temp`/`humidity` are calibrated at write time, so changing `temp_offset` does not
  retroactively change an already-stored value until the next reading.

## References

- Related: [[2026-07-16-sensor-model-queryset-manager]]
