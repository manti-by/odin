---
title: 'Boiler logging — hourly mode and setpoint snapshots'
date: '2026-11-10'
type: implementation
status: resolved
session_id: ses_boiler_logging_2026_11_10
services: [boiler, boiler-models, boiler-services, scheduler, rq]
branch: ch-9-boiler-logging
tickets: [CH-9]
tags: [boiler, logging, rq, scheduler, models]
related: [2026-11-10-ch-9-boiler-logging.md, 2026-09-27-boiler-live-status-api.md, 2026-09-18-mnt-208-boiler-dashboard.md, 2026-09-17-mnt-206-boiler-mode-controller.md]
---
# Boiler logging — hourly mode and setpoint snapshots

## TL;DR

Added a `BoilerLog` model to the boiler app and an hourly job that stores the boiler's mode and
setpoints, so the heating history becomes queryable from the database instead of being visible only
in the live status API. The snapshot is read exactly the way `GET /api/v1/boiler/status/` reads it —
the mode in effect plus the setpoints from the saved override file — and is written by the RQ worker,
the first real job on the queue handle that had been sitting unused in `odin/apps/core/scheduler.py`.

---

## Overview

The ticket asked for an hourly `BoilerLog` row carrying `hcmode`, `flow_temp`, `hwc_temp` and
`created_at`, produced by a service, a management command and a "rq schedule" driven from
`odin/apps/core/scheduler.py`.

Three decisions came from the ticket questions:

- `flow_temp`/`hwc_temp` are read from the override file, the way `BoilerStatusView.target_temp` /
  `hwc_temp` are derived — not from the live eBus fields.
- `hcmode` stores the display mode (`BoilerMode`: `heating` / `mixed` / `off` / `boiling`), not the
  raw SetMode token.
- The hourly job enqueues the callable `log_boiler_status` on the existing `default` queue handle
  instead of calling a management command inline.

One consequence worth remembering: because the setpoints come from the override file, a snapshot taken
while the boiler runs on its panel settings (no override) stores `NULL` for `flow_temp` and
`hwc_temp`. The mode is still recorded, because `BoilerModeService.get_current_mode()` falls back to
the mode decided from the weather and the pumps.

## Step 1 — `BoilerLog` model and the `BoilerMode` enum move

**File:** `odin/apps/boiler/models.py` (new), `odin/apps/boiler/migrations/0001_initial.py` (new)

The boiler app had no `models.py` at all. `BoilerMode` moved here from `services/mode.py`:

```python
class BoilerMode(models.TextChoices):
    HEATING = "heating", "Heating"
    MIXED = "mixed", "Mixed"
    OFF = "off", "Off"
    BOILING = "boiling", "Boiling"
    CLEAR_OVERRIDE = "clear_override", "Clear override"


class BoilerLog(models.Model):
    """One snapshot of the boiler's mode and setpoints."""

    hcmode: models.CharField[BoilerMode] = models.CharField(
        max_length=16, choices=BoilerMode.choices, verbose_name=_("Mode")
    )
    flow_temp: models.IntegerField[int] | None = models.IntegerField(...)
    hwc_temp: models.IntegerField[int] | None = models.IntegerField(...)
    created_at: models.DateTimeField[datetime] = models.DateTimeField(auto_now_add=True, db_index=True, ...)
```

Why the enum moved:

- The model needs `BoilerMode.choices`, and a models → services import is the direction this codebase
  avoids (`odin/apps/relays/models.py:128` keeps its service import inside the method for exactly that
  reason).
- Every other enum in the repo already lives in its app's `models.py` — `SensorType`, `RelayType` /
  `RelayState` / `RelayMode`, `FetchStatus`, `WeatherProvider`.
- `services/mode.py` now re-exports it (`from odin.apps.boiler.models import BoilerMode`), so
  `from odin.apps.boiler.services.mode import BoilerMode` and
  `from odin.apps.boiler.services import BoilerMode` keep working unchanged.

`objects = models.Manager()` is declared explicitly, matching `RelayLog`; `ty` otherwise reports
`Class BoilerLog has no attribute objects`.

## Step 2 — the shared state reader

**File:** `odin/apps/boiler/services/state.py` (new)

```python
@dataclass(frozen=True)
class BoilerState:
    mode: BoilerMode
    flow_temp: int | None
    hwc_temp: int | None


def get_current_state() -> BoilerState:
    override = BoilerStatusService().current_override()
    flow_temp = hwc_temp = None
    if override:
        _, flow_temp, hwc_temp = parse_override(override)

    return BoilerState(mode=BoilerModeService().get_current_mode(), flow_temp=flow_temp, hwc_temp=hwc_temp)
```

The API view now calls the same helper, so "the same way as `BoilerStatusView`" is structural rather
than a comment: if the view's derivation changes, the log follows.

**File:** `odin/api/v1/boiler/views.py`

```python
service = BoilerStatusService()
override = service.current_override()
state = get_current_state()

data = {
    "mode": state.mode,
    "target_temp": state.flow_temp,
    "hwc_temp": state.hwc_temp,
    ...
```

The view still reads `current_override()` itself for `override_active` / `override_updated_at`, so the
override file is read twice per request. The pair is written atomically by
`BoilerStatusService._save_state`, so the only exposure is a stale `override_active` flag if the
override is cleared between the two reads.

## Step 3 — the logging service

**File:** `odin/apps/boiler/services/log.py` (new)

```python
class BoilerLogService:
    """Persist the boiler's current state as ``BoilerLog`` rows."""

    def get_state(self) -> BoilerState:
        return get_current_state()

    def log(self) -> BoilerLog:
        state = self.get_state()
        entry = BoilerLog.objects.create(hcmode=state.mode, flow_temp=state.flow_temp, hwc_temp=state.hwc_temp)
        logger.info(f"Boiler state logged: {entry}")
        return entry


def log_boiler_status() -> BoilerLog:
    """Scheduler entry point: store one snapshot of the current boiler state."""
    return BoilerLogService().log()
```

`log_boiler_status` is a module-level function on purpose: RQ serializes the job by import path
(`odin.apps.boiler.services.log.log_boiler_status`), which a bound method would not give it.

## Step 4 — management command

**File:** `odin/apps/boiler/management/commands/boiler_log.py` (new)

A plain `BaseCommand` (the other boiler commands use `BaseCommand`, while `update_voltage` /
`video_scan` use `command_log`'s `LoggedCommand`) that calls `log_boiler_status()` and prints the
stored row.

## Step 5 — hourly RQ job

**File:** `odin/apps/core/scheduler.py`

```python
@scheduler.scheduled_job("interval", hours=1, id="log_boiler_status", max_instances=1)
def schedule_log_boiler_status():
    """Store an hourly snapshot of the boiler's mode and setpoints. ..."""
    from odin.apps.boiler.services.log import log_boiler_status

    try:
        queue.enqueue(log_boiler_status)
    except Exception:
        logger.exception("Boiler log job could not be enqueued")
```

- The job function imports the callable locally, mirroring the commented-out `update_boiler_mode` job
  below it, so the core app has no module-level dependency on the boiler app.
- The `except Exception` guard keeps a Redis outage from surfacing as an unhandled APScheduler job
  error; the next tick retries.
- `max_instances=1` matches `video_scan` and prevents a slow run from stacking up.

This is the first job that actually uses the `queue` handle declared at
`odin/apps/core/scheduler.py:12`; `configs/worker.service` already runs `manage.py rqworker default`,
so no new service unit is needed. The callable is not `queue_`-prefixed, which is a deliberate
exception to the background-task convention in `AGENTS.md` (recorded there).

## Test Results

- New: `odin/tests/services/test_boiler_log.py` — 7 tests (heating / boiling / mixed overrides,
  panel mode with and without weather, the `log_boiler_status` entry point, and the scheduler
  enqueue wiring).
- New: `odin/tests/commands/test_boiler_log.py` — 2 tests (row created, row printed).
- Shared `boiler_state` fixture added to `odin/tests/conftest.py`; the two older boiler test modules
  keep their local copies.
- `9 passed` for the two new modules on the in-memory SQLite settings.
- `odin/tests/api/test_boiler.py` (8) and `odin/tests/services/test_boiler_mode_controller.py` (24)
  pass, so the view refactor and the enum move are behaviour-preserving.
- `ruff check` / `ruff format --check` clean, `ty check` clean, `makemigrations --check` reports no
  changes, `manage.py check` clean.
- The PostgreSQL-backed full run could not be executed in the build sandbox (no PostgreSQL or Redis
  server); the full `odin/` suite on SQLite reported `594 passed`, with the remaining failures being
  Redis connection errors and SQLite's missing `DISTINCT ON` — none in boiler, scheduler or the new
  modules.

## Follow-ups

- Run `make test` (PostgreSQL) before merging; the new migration is `boiler/0001_initial`.
- `BoilerLog` rows are never pruned. If the table grows, add a retention job alongside the other
  scheduled jobs.
- No admin registration and no read API for the log rows — the ticket did not ask for them.
- The `hcmode` column stores a `BoilerMode` value while the name still suggests the raw eBus token
  (`auto`/`heat`/`water`/`off`); the field name follows the ticket, the value follows the ticket
  answer.

## References

- Related: [[2026-11-10-ch-9-boiler-logging]] — the CH-9 ticket summary page for the same session
- Related: [[2026-09-27-boiler-live-status-api]] — the status API the snapshot mirrors
- Related: [[2026-09-18-mnt-208-boiler-dashboard]] — boiler tile and the status endpoint
- Related: [[2026-09-17-mnt-206-boiler-mode-controller]] — `BoilerModeService`, the mode decision
