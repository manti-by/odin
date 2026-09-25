# odin Wiki — Index

Session knowledge base for the odin project - one Markdown page per debugging
chase, investigation, code review, or set of changes. See [README.md](README.md) for conventions
and [TEMPLATE.md](TEMPLATE.md) for the page template. New pages are added and updated automatically
by the plugin.

## Pages

_Newest first._

- [Silk profiler unreachable — SPA catch-all shadows /silk/](pages/2026-09-24-silk-route-spa-catchall-shadow.md) — Local dev server was down, and `/silk/` also served the SPA `index.html` because the catch-all `re_path` didn't exclude `silk`; added `silk(?:$|/)` to the lookahead (2026-09-24)
- [Sensor relation FKs and denormalized readings](pages/2026-09-24-sensor-fks-and-denormalized-readings.md) — Migrated `SensorLog.sensor`, `Sensor.relay`, and `Sensor.linked_sensor` from char columns to nullable FKs, dropped the legacy `*_old` columns, and cached `temp`/`humidity` on `Sensor`; `is_alive` now reads `updated_at` (2026-09-24/25)
- [MNT-218: Split dashboard API](pages/2026-09-23-mnt-218-split-dashboard-api.md) — Split the aggregate dashboard API into per-model endpoints under `odin/api/v1/` and moved the SPA to per-tile hooks/APIs; removed the old `core/dashboard/` view, serializer, and services (2026-09-23)
- [Relay mode computed on read](pages/2026-09-23-relay-mode-compute-on-read.md) — `SERVO-BR`/`SERVO-HL` showed different modes because `mode` is a persisted snapshot; compute `mode`/`target_state` on read via `Relay.get_target_state()` in the CRUD and dashboard serializers (2026-09-23)
- [MNT-217: Relay schedule component](pages/2026-09-22-mnt-217-relay-schedule-component.md) — Added the relay schedule modal, schedule-aware relay serializers with period-overlap validation, and schedule API endpoints (2026-09-22)
- [ESP8266 relay indicators: SVG icons + mode tooltip](pages/2026-09-21-esp8266-indicator-icons.md) — Replaced `is_on`-based dots with ON/OFF SVG icons plus grey/red dots for UNKNOWN/IGNORED modes, and moved the relay `mode` into a `title` tooltip (2026-09-21)
- [MNT-215: Midseason mode](pages/2026-09-19-mnt-215-midseason-mode.md) — Midseason runs the pump only in the active daytime hour (`hour >= 6 and hour % 3 == 0`) and keeps servos open; `RelayState.IGNORED` was removed (2026-09-19)
- [MNT-207: Wire boiler mode controller into scheduler tick / cron](pages/2026-09-18-mnt-207-wire-boiler-mode-controller-into-scheduler-tick-cron.md) — Added `BoilerModeController`/`run_boiler_mode_controller` and a 5-minute `update_boiler_mode` scheduler job — the job is currently commented out (disabled 2026-09-22) (2026-09-18)
- [MNT-208: Boiler dashboard](pages/2026-09-18-mnt-208-boiler-dashboard.md) — Added the boiler dashboard tile and `GET /api/v1/boiler/status/`, plus `schedule.py`/`mode.py`/`status.py` support; fixed the Saturday boil/clear schedule and the tile error guard (2026-09-18)
- [Relay state/mode refactor — review, test sync, and fixes](pages/2026-09-18-relay-state-mode-refactor.md) — Reviewed and synced the relay `state`/`mode` column refactor, fixed API update not populating `state` and reads overwriting it; 259 tests green (2026-09-18)
- [MNT-206: Boiler mode controller](pages/2026-09-17-mnt-206-boiler-mode-controller.md) — Split the boiler `services.py` into a package and added the pure `BoilerModeService` decision service; `BoilerService` renamed `BoilerStatusService` (2026-09-17)
- [ebusd lost its device config (boiler reads all failed) + refresh timer disabled](pages/2026-09-11-ebusd-config-load-boiler-refresh.md) — `boiler_status` reads all failed because the long-running ebusd lost outbound HTTPS (no Vaillant config loaded) and `boiler-refresh.timer` was disabled; fixed via restart, `--scanconfig=08`, and enabling the timer (2026-09-11)
- [Relay state sync — admin refresh and Redis consumer](pages/2026-09-11-relay-state-redis-consumer.md) — Refreshed relay state in the admin and extended `consume_sensors` (now `consumer`) to subscribe to `relays:control`; no new systemd service (2026-09-11)
- [Add self-referential related_relay field to Relay](pages/2026-09-11-add-related-relay-field.md) — Added the nullable `related_relay` self-FK + migration 0006 and surfaced it in the relay admin (2026-09-11)
- [Fix React SPA dev-mode issues: docs, proxy, base path, StrictMode Loading bug](pages/2026-08-24-react-spa-dev-mode-debug.md) — Synced docs with the React SPA migration; scoped Vite `base` to production and removed the `isMountedRef` guard that left tiles on "Loading…" under StrictMode (2026-08-24)
- [Proterm Lynx 25 eBus Protocol Investigation](pages/2026-08-11-proterm-lynx-25-ebus-protocol.md) — eBus protocol investigation of the Vaillant BAI boiler: reads mapped; the 2026-08-11 write failures were traced to malformed `SetMode` frames, and correctly framed writes work (2026-08-11)
- [React frontend PR review — apply CodeRabbit + coding-guideline fixes](pages/2026-07-21-react-frontend-pr-review-fixes.md) — Reviewed the React frontend migration + PR #14 CodeRabbit comments; applied non-security fixes and coding-guideline cleanups, and wired frontend checks into CI/Makefile (2026-07-21)
- [Mock Kafka and systemctl in dashboard tests for CI](pages/2026-07-17-mock-kafka-systemctl-in-tests.md) — Mocked the Kafka relay refresh and `systemd_status` in dashboard tests to stop `NoBrokersAvailable`/`FileNotFoundError` on CI; Kafka was later replaced by Redis (2026-07-17)
- [Sensor Model QuerySet and Manager Investigation](pages/2026-07-16-sensor-model-queryset-manager.md) — Investigation of `Sensor`, `SensorQuerySet`/`SensorManager`, and `SensorLogManager.current()`; the model has since moved to FKs and denormalized readings (2026-07-16)
- [Codebase search — GitHub/PR webhooks and notifications](pages/2026-07-16-github-pr-webhooks-search.md) — Exhaustive search found no GitHub integration, PR processing, or notification mark-as-read logic in the codebase (2026-07-16)
- [Merge/Rebase PR Comment Handlers — Not Found](pages/2026-07-16-merge-rebase-pr-comment-handlers.md) — Exhaustive search found no GitHub PR/webhook or notification read-state code (2026-07-16)
- [PR merge/rebase comment listener marks as read despite errors](pages/2026-07-16-merge-rebase-pr-comment-listener.md) — Debug notes on a listener that marks notifications read despite errors; verified no such code exists in odin — kept as reference (2026-07-16)
- [Fix type errors and verify CI flow](pages/2026-07-16-fix-type-errors-ci-flow.md) — Fixed 9 `ty` errors, patched 2 test stubs, and ran `make ci` to 193/193 green (2026-07-16)

## By topic

_Topic clusters maintained by the Consistency Agent; topics with the most pages first._

### Relay control (state, mode, schedules, indicators)

- [Add self-referential related_relay field to Relay](pages/2026-09-11-add-related-relay-field.md)
- [Relay state sync — admin refresh and Redis consumer](pages/2026-09-11-relay-state-redis-consumer.md)
- [Relay state/mode refactor — review, test sync, and fixes](pages/2026-09-18-relay-state-mode-refactor.md)
- [MNT-215: Midseason mode](pages/2026-09-19-mnt-215-midseason-mode.md)
- [ESP8266 relay indicators: SVG icons + mode tooltip](pages/2026-09-21-esp8266-indicator-icons.md)
- [MNT-217: Relay schedule component](pages/2026-09-22-mnt-217-relay-schedule-component.md)
- [Relay mode computed on read](pages/2026-09-23-relay-mode-compute-on-read.md)

### Boiler / eBus control

- [Proterm Lynx 25 eBus Protocol Investigation](pages/2026-08-11-proterm-lynx-25-ebus-protocol.md)
- [ebusd lost its device config (boiler reads all failed) + refresh timer disabled](pages/2026-09-11-ebusd-config-load-boiler-refresh.md)
- [MNT-206: Boiler mode controller](pages/2026-09-17-mnt-206-boiler-mode-controller.md)
- [MNT-207: Wire boiler mode controller into scheduler tick / cron](pages/2026-09-18-mnt-207-wire-boiler-mode-controller-into-scheduler-tick-cron.md)
- [MNT-208: Boiler dashboard](pages/2026-09-18-mnt-208-boiler-dashboard.md)

### Dashboard API & frontend SPA

- [React frontend PR review — apply CodeRabbit + coding-guideline fixes](pages/2026-07-21-react-frontend-pr-review-fixes.md)
- [Fix React SPA dev-mode issues: docs, proxy, base path, StrictMode Loading bug](pages/2026-08-24-react-spa-dev-mode-debug.md)
- [MNT-218: Split dashboard API](pages/2026-09-23-mnt-218-split-dashboard-api.md)

### GitHub integration & notifications

- [Codebase search — GitHub/PR webhooks and notifications](pages/2026-07-16-github-pr-webhooks-search.md)
- [Merge/Rebase PR Comment Handlers — Not Found](pages/2026-07-16-merge-rebase-pr-comment-handlers.md)
- [PR merge/rebase comment listener marks as read despite errors](pages/2026-07-16-merge-rebase-pr-comment-listener.md)

### Sensor data model

- [Sensor Model QuerySet and Manager Investigation](pages/2026-07-16-sensor-model-queryset-manager.md)
- [Sensor relation FKs and denormalized readings](pages/2026-09-24-sensor-fks-and-denormalized-readings.md)

### Type checking, CI & test infrastructure

- [Fix type errors and verify CI flow](pages/2026-07-16-fix-type-errors-ci-flow.md)
- [Mock Kafka and systemctl in dashboard tests for CI](pages/2026-07-17-mock-kafka-systemctl-in-tests.md)

### Django admin & dev tooling

- [Silk profiler unreachable — SPA catch-all shadows /silk/](pages/2026-09-24-silk-route-spa-catchall-shadow.md)
