---
title: 'CH-9: Boiler logging'
date: '2026-11-10'
type: implementation
status: resolved
session_id: ses_e391db859ffe3C5XRczuMAHjcQ
services: [boiler, boiler-models, boiler-services, scheduler, rq, api-boiler, test_boiler_log]
branch: ch-9-boiler-logging
tickets: [CH-9]
tags: [boiler, logging, rq, scheduler, models]
related: [2026-11-10-boiler-logging.md, 2026-09-27-boiler-live-status-api.md, 2026-09-18-mnt-208-boiler-dashboard.md]
---

# CH-9: Boiler logging

## TL;DR

CH-9 records the boiler's mode and setpoints once an hour: a new `BoilerLog` model in the boiler
app, a `BoilerLogService` / `log_boiler_status` pair that reads the state exactly the way
`BoilerStatusView` does, a `boiler_log` management command, and an hourly APScheduler job that
enqueues the callable on the RQ `default` queue. Full suite: **645 passed** on PostgreSQL,
**226 passed** for `mcp_server`.

## Overview

The ticket asked for `hcmode`, `flow_temp`, `hwc_temp` and `created_at` stored hourly, produced by a
service, a management command and a scheduled job in `odin/apps/core/scheduler.py`. Three decisions
were settled on the ticket before implementation:

- The setpoints come from the saved override file — the way `BoilerStatusView.target_temp` /
  `hwc_temp` are derived — not from the live `FlowTempDesired` / `HwcTempDesired` bus fields.
- `hcmode` stores the display mode (`BoilerMode`: `heating` / `mixed` / `off` / `boiling`), not the
  raw SetMode token, while keeping the ticket's column name.
- The job enqueues the callable `log_boiler_status` on the existing queue handle instead of calling
  a management command inline. It is the first production use of RQ in this project.

Consequence worth remembering: with no override the boiler runs on its panel settings, so a snapshot
stores `NULL` for `flow_temp` and `hwc_temp`. The mode is still recorded, because
`BoilerModeService.get_current_mode()` falls back to the mode decided from the weather and pumps.

## Step 1 — `BoilerLog` model and the `BoilerMode` enum

**File:** `odin/apps/boiler/models.py` (new), `odin/apps/boiler/migrations/0001_initial.py` (new)

The boiler app had no models before, so this is its first model and its `0001_initial` migration.

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
    flow_temp: models.IntegerField[int] | None = models.IntegerField(
        null=True, blank=True, verbose_name=_("Flow temperature")
    )
    hwc_temp: models.IntegerField[int] | None = models.IntegerField(
        null=True, blank=True, verbose_name=_("Hot-water temperature")
    )

    created_at: models.DateTimeField[datetime] = models.DateTimeField(
        auto_now_add=True, db_index=True, verbose_name=_("Created at")
    )

    objects = models.Manager()

    class Meta:
        verbose_name = _("boiler log")
        verbose_name_plural = _("boiler logs")
        ordering = ("-created_at",)
```

Notes:

- The temperatures are nullable integers (the override carries whole degrees, `None` when the field
  is `-`/not controlled or when no override is active) — not floats.
- `BoilerMode` moved here from `services/mode.py`, which now imports it back
  (`from odin.apps.boiler.models import BoilerMode`). The model needs the choices, and every other
  enum in this repo lives in its app's `models.py`; the re-export keeps
  `from odin.apps.boiler.services.mode import BoilerMode` and
  `from odin.apps.boiler.services import BoilerMode` working.
- `objects = models.Manager()` is explicit, matching `RelayLog`; `ty` otherwise reports
  `Class BoilerLog has no attribute objects`.

## Step 2 — shared state reader

**File:** `odin/apps/boiler/services/state.py` (new)

```python
@dataclass(frozen=True)
class BoilerState:
    """Boiler mode plus the setpoints saved in the active override."""

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

`odin/api/v1/boiler/views.py` now builds its `mode` / `target_temp` / `hwc_temp` from the same
helper, so the API and the log cannot drift. The view keeps its own `BoilerStatusService()` for
`override_active`, `override_updated_at()`, `is_alive()` and `status()`, so the override file is read
twice per request — harmless, since `_save_state` writes it atomically with `os.replace`.

## Step 3 — logging service and the RQ callable

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

`log_boiler_status` is a module-level function returning the stored `BoilerLog`: RQ serializes a job
by import path (`odin.apps.boiler.services.log.log_boiler_status`), so the worker rebuilds it from
the queue payload. The job never touches ebusd — the mode comes from the override file plus the
weather/pump decision — so an ebusd outage does not stop the hourly record.

## Step 4 — `boiler_log` management command

**File:** `odin/apps/boiler/management/commands/boiler_log.py` (new)

```python
class Command(BaseCommand):
    help = description = "Store a snapshot of the current boiler mode and setpoints."

    def handle(self, *args, **options):
        entry = log_boiler_status()

        self.stdout.write(self.style.SUCCESS(f"logged {entry}"))
```

A plain `BaseCommand`, like `boiler_set` / `boiler_status` in the same app, for manual runs and
diagnostics (`manage.py boiler_log`).

## Step 5 — hourly RQ job

**File:** `odin/apps/core/scheduler.py`

APScheduler's decorator registers the job; the function only enqueues the callable:

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

- `queue` is the `get_queue(name="default", is_async=settings.QUEUE_SCHEDULED_TASKS)` handle declared
  at `odin/apps/core/scheduler.py:12`, unused until this job; the worker already runs as
  `manage.py rqworker default` (`configs/worker.service`), so no new service unit.
- The import is function-local, mirroring the commented-out `update_boiler_mode` job below it, which
  keeps the core app free of a module-level boiler dependency during app loading.
- `max_instances=1` prevents overlap; the `try/except` keeps a Redis outage from surfacing as an
  unhandled job error, and the next tick retries.
- The callable is not `queue_`-prefixed — a deliberate, documented exception to the background-task
  convention in `AGENTS.md`.

## Test Results

- `odin/tests/services/test_boiler_log.py` — 7 tests: heating / boiling / mixed overrides, panel mode
  with and without weather, the `log_boiler_status` entry point, and the scheduler enqueue wiring.
- `odin/tests/commands/test_boiler_log.py` — 2 tests: the row is created, the row is printed.
- `odin/tests/conftest.py` gained a shared `boiler_state` fixture (temporary override file paths).
- `odin/tests/api/test_boiler.py` (8) and `odin/tests/services/test_boiler_mode_controller.py` pass,
  so the view refactor and the enum move are behaviour-preserving.
- Full `odin/` suite on PostgreSQL: **645 passed**. `mcp_server/`: **226 passed**.
- `ruff check` / `ruff format --check` clean, `ty check` clean, `pre-commit run` (incl. bandit) all
  hooks pass, `makemigrations --check` reports no changes, `manage.py check` clean.
- The repo has no coverage tooling configured, so no coverage figure is claimed here.

## Follow-ups

- `BoilerLog` rows are never pruned — add a retention job if the table needs bounding (24 rows/day).
- No Django admin registration and no read API for the rows; neither was requested.
- `hcmode` keeps the ticket's name while storing a `BoilerMode` value; the raw eBus token
  (`auto`/`heat`/`water`/`off`) stays in the override file only.
- The `boiler_state` fixture is still duplicated in two older boiler test modules and can now be
  dropped in favour of the conftest copy.

## References

- Related: [[2026-11-10-boiler-logging]] — the long-form step-by-step write-up of the same session
- Related: [[2026-09-27-boiler-live-status-api]] — the status API the snapshot mirrors
- Related: [[2026-09-18-mnt-208-boiler-dashboard]] — boiler tile and the status endpoint
- Related: [[2026-09-17-mnt-206-boiler-mode-controller]] — `BoilerModeService`, the mode decision
