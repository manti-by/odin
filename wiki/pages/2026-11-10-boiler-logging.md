---
title: 'Boiler logging — hourly mode and setpoint snapshots'
date: '2026-11-10'
type: implementation
status: resolved
session_id: ses_e391db859ffe3C5XRczuMAHjcQ
services: [boiler, boiler-models, boiler-services, scheduler, rq, api-boiler, django-admin]
branch: ch-9-boiler-logging
tickets: [CH-9]
tags: [boiler, logging, rq, scheduler, models, django-admin]
related: [2026-11-10-ch-9-boiler-logging.md, 2026-09-27-boiler-live-status-api.md, 2026-09-18-mnt-208-boiler-dashboard.md, 2026-09-17-mnt-206-boiler-mode-controller.md]
---

# Boiler logging — hourly mode and setpoint snapshots

> Rewritten 2026-11-25: the original implementation stored only override-file setpoints, which left
> `flow_temp` / `hwc_temp` NULL in panel mode. The log now falls back to the live eBus setpoints shown
> on the dashboard, stores every readable eBus field in a JSON `context`, has an admin page, and the
> old NULL-only rows were deleted.

## TL;DR

CH-9 added an hourly `BoilerLog` row with the mode in effect plus the active setpoints, written by
`BoilerLogService` through the RQ `default` queue. A later fix made the setpoints useful in panel
mode: override values win when present, otherwise the service reads the same live eBus fields the
dashboard tile displays (`FlowTempDesired`, `StorageTempDesired`). Each row also carries a JSON
`context` with every field from `BoilerStatusService.status()` — the complete set of eBus values the
daemon currently exposes. `BoilerLog` is registered in Django admin, and the 44 historical rows with
NULL setpoints were removed because that data could not be backfilled.

---

## Symptom (2026-11-25)

The new admin page listed `mixed` rows with empty `flow_temp` / `hwc_temp`, while the dashboard tile
showed real numbers (`Flow 35°C`, `Tank 45°C`).

Evidence:

- `SELECT count(*) FROM boiler_boilerlog` → 44 rows, all with both setpoint columns NULL.
- `/var/lib/boiler-set/state` did not exist: the boiler was running on its panel settings, with no
  SetMode override.
- `GET /api/v1/boiler/status/` also returned `target_temp: null` / `hwc_temp: null` in panel mode —
  those fields are override-derived too.
- `ebusctl read -f -c bai FlowTempDesired` → `35.00`, `StorageTempDesired` → `45.00`, and the tile
  renders exactly those two live fields (`frontend/src/components/tile/BoilerTile.tsx:79,83`).

Root cause: `get_current_state()` reads setpoints only from the override file. The original ticket
explicitly chose that source, so a snapshot without an override stored NULL even though the panel
setpoints were available on the bus.

## Overview of the feature

- `BoilerLog` is the boiler app's first model (`odin/apps/boiler/models.py`), with `hcmode`
  (`BoilerMode`), nullable `flow_temp` / `hwc_temp`, a JSON `context`, and indexed `created_at`;
  ordering is newest first.
- `get_current_state()` (`odin/apps/boiler/services/state.py`) still supplies the mode in effect and
  the override setpoints to `GET /api/v1/boiler/status/`. The API is deliberately unchanged.
- `BoilerLogService` (`odin/apps/boiler/services/log.py`) is the only place that augments those
  override setpoints with live eBus values. It takes an optional `BoilerStatusService` for injection,
  reads `status()` once per snapshot, and reuses that dict for both the fallback setpoints and the
  stored `context`. `status()` catches `EbusdError` per field, so an outage records `error: ...`
  strings in the context rather than losing the whole row.
- `log_boiler_status()` is a module-level function (RQ serializes jobs by import path), exposed via
  `manage.py boiler_log` and scheduled hourly in `odin/apps/core/scheduler.py` on the `default` queue.
- `BoilerLogAdmin` (`odin/apps/boiler/admin.py`) registers the model with `list_display`,
  `search_fields` and `list_filter`, mirroring `SensorLogAdmin`.

## Step 1 — model and enum

**File:** `odin/apps/boiler/models.py`, `odin/apps/boiler/migrations/0001_initial.py`,
`odin/apps/boiler/migrations/0002_boilerlog_context.py`

`BoilerMode` moved here from `services/mode.py` (and is re-exported there), because every other enum
in the repo lives in its app's `models.py`. The fields are nullable integers on purpose: the log can
still record the mode when eBus is unreachable. `context` is a `JSONField(default=dict, blank=True)`
added by `0002_boilerlog_context` and filled with the live status dict. `objects = models.Manager()`
is explicit so `ty` does not complain about a missing manager.

## Step 2 — shared state reader (unchanged)

**File:** `odin/apps/boiler/services/state.py`

```python
def get_current_state() -> BoilerState:
    override = BoilerStatusService().current_override()
    flow_temp = hwc_temp = None
    if override:
        _, flow_temp, hwc_temp = parse_override(override)

    return BoilerState(mode=BoilerModeService().get_current_mode(), flow_temp=flow_temp, hwc_temp=hwc_temp)
```

`BoilerStatusView` still builds `mode` / `target_temp` / `hwc_temp` from this helper. Leaving it
alone keeps the API contract stable; only the log needs live values.

## Step 3 — live setpoint fallback and the eBus context

**File:** `odin/apps/boiler/services/log.py`

```python
class BoilerLogService:
    def __init__(self, status: BoilerStatusService | None = None):
        self.status = status or BoilerStatusService()

    def get_state(self, status: dict[str, str] | None = None) -> BoilerState:
        status = self.status.status() if status is None else status
        state = get_current_state()
        return BoilerState(
            mode=state.mode,
            flow_temp=state.flow_temp if state.flow_temp is not None else parse_temp(status.get("FlowTempDesired", "")),
            hwc_temp=state.hwc_temp if state.hwc_temp is not None else parse_temp(status.get("StorageTempDesired", "")),
        )

    def log(self) -> BoilerLog:
        status = self.status.status()
        state = self.get_state(status)
        return BoilerLog.objects.create(
            hcmode=state.mode,
            flow_temp=state.flow_temp,
            hwc_temp=state.hwc_temp,
            context=status,
        )
```

Rules to remember:

- `log()` calls `status()` once per snapshot and reuses that dict for both the fallback setpoints and
  `context`, so the columns and the JSON describe the same eBus read.
- **File:** `odin/apps/boiler/services/status.py` — `status()` iterates `STATUS_FIELDS`:
  `FlowTempDesired`, `HwcTempDesired`, `StorageTempDesired`, `FlowTemp`, `ReturnTemp`, `StorageTemp`,
  `ModulationDesired`, `Status01`, `Status02`. These are the nine bai fields that currently return
  data; `ebusctl find -c bai` reports the rest as "no data stored". Values stay raw strings (e.g.
  `"37.12;ok"`), and a failed read is stored as `"error: ..."` by `status()`.
- The saved override wins per field. A field written as `-` (not controlled) falls back to the live
  value, which is what the boiler actually uses from its panel.
- `StorageTempDesired` is the tank field the dashboard labels "Tank"; `HwcTempDesired` is not used
  for the `hwc_temp` column, but it is preserved in `context`.
- **File:** `odin/apps/boiler/services/status.py` — `parse_temp()` (formerly private `_parse_temp`)
  now accepts both override integers (`45`) and eBus decimals (`45.00`), and maps `-` or garbage to
  `None`. `parse_override()` uses the same helper.
- The mode still comes from `BoilerModeService`, which needs no eBus connection, so the job records
  a useful row even when the daemon is down.

## Step 4 — management command and hourly job

**File:** `odin/apps/boiler/management/commands/boiler_log.py`, `odin/apps/core/scheduler.py`

`manage.py boiler_log` calls `log_boiler_status()` and prints the row. APScheduler enqueues the same
callable on the `default` queue hourly (`id="log_boiler_status"`, `max_instances=1`); the function is
not `queue_`-prefixed, a documented exception because it lives with the boiler services. RQ's worker
(`configs/worker.service`) already consumes that queue.

## Step 5 — Django admin

**File:** `odin/apps/boiler/admin.py` (new 2026-11-25)

```python
@admin.register(BoilerLog)
class BoilerLogAdmin(admin.ModelAdmin):
    list_display = ("hcmode", "flow_temp", "hwc_temp", "created_at")
    search_fields = ("hcmode",)
    list_filter = ("hcmode", "created_at")
```

Mirrors `SensorLogAdmin`. No read API for the rows was requested.

## Step 6 — data cleanup

All 44 existing rows had both setpoints NULL. They could not be backfilled: the historical panel
setpoints were never written anywhere, so they were deleted with
`DELETE FROM boiler_boilerlog WHERE flow_temp IS NULL OR hwc_temp IS NULL;`. New rows created after
the fix carry real values (except when eBus itself is unreachable). Migration
`0002_boilerlog_context` was applied to the live database; the row written before the migration had
`context = {}` and was removed, so the remaining sample row has all nine eBus fields in `context`.

## Tests

- `odin/tests/services/test_boiler_log.py`: override precedence (heating/boiling/mixed), live
  fallback in panel mode with and without weather, context equals the full `STATUS_FIELDS` dict,
  `EbusdError` per field → `error: ...` strings in context and NULL setpoints, entry point,
  scheduler wiring.
- `odin/tests/commands/test_boiler_log.py`: command creates and prints the row, including context.
- `boiler_live_status` in `odin/tests/conftest.py` stubs `BoilerStatusService.status` with a full
  nine-field dict so no test talks to the eBus daemon.
- 10/10 log tests pass; 646 tests pass on PostgreSQL; `ruff check`, `ruff format --check`, `ty check`
  and targeted `pre-commit run` are clean.

## Follow-ups

- `BoilerLog` rows are never pruned — 24 rows/day; add a retention job if the table needs bounding.
- The API's `target_temp` / `hwc_temp` remain override-only; clients wanting live setpoints should
  read `status.FlowTempDesired` / `status.StorageTempDesired`, as the tile does.
- `hcmode` keeps the ticket's column name while storing a `BoilerMode` value, not the raw eBus token.

## References

- Related: [[2026-11-10-ch-9-boiler-logging]] — ticket-level write-up of the original implementation
- Related: [[2026-09-27-boiler-live-status-api]] — the fix that added live eBus fields to the status API
- Related: [[2026-09-18-mnt-208-boiler-dashboard]] — boiler tile and the status endpoint
- Related: [[2026-09-17-mnt-206-boiler-mode-controller]] — `BoilerModeService`, the mode decision
