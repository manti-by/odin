# odin Wiki — Index

Session knowledge base for the odin project - one Markdown page per debugging
chase, investigation, code review, or set of changes. See [README.md](README.md) for conventions
and [TEMPLATE.md](TEMPLATE.md) for the page template. New pages are added and updated automatically
by the plugin.

## Pages

_Newest first._

- [RelayTargetStateService review — antifreeze fail-safe and rule order](pages/2026-10-26-relay-target-state-antifreeze-review.md) — Reviewed the uncommitted antifreeze fail-safe rewrite: `None` from `get_weather_mode()` swallowed the whole `-8…10 °C` band and force/override were dropped for servos and valves (98 of 205 relay/boiler tests failing); recorded the agreed rule order (fail-safe for missing or >2 h-old weather only, antifreeze beats a forced stop, servos always open in midseason, `>= 10 °C` is midseason) and the change list for the service (2026-10-26)
- [MNT-255: Override by schedule](pages/2026-10-25-mnt-255-override-by-schedule.md) — Added a time-based `context["override_schedule"]` applied right after `force_state` for pumps, servos and valves, reporting the new `RelayMode.OVERRIDE` (migration 0012); also re-baselined the midseason tests to the already-merged 10/17 band, and added an antifreeze fail-safe for missing or unusable weather that outranks `force_state` and the override, while usable weather in the `-8 … 10 °C` default band still reaches the cycle, the schedule and servo regulation — 210 relay tests pass, 539 full-suite tests on PostgreSQL (MNT-255 and MNT-259, merged 2026-10-26) (2026-10-25)

- [MNT-253 — Midseason humidity & wind research](pages/2026-10-22-mnt-253-midseason-humidity-wind-research.md) — Researched how outside temp/humidity/wind act on the house; the band should gate on the Steadman apparent temperature `AT = Ta + 0.33e − 0.70ws − 4.00`, asymmetrically (raw bottom edge, feels-like top edge); validated on 16 months of production data — wind adds only ~3%/m·s⁻¹ to the indoor fall rate, the band would gain 618 short windy spells/lose 41 h, and macOS TCC was found blocking psql from the LAN (2026-10-22)

- [MNT-250 spec review — schedule cycle rule](pages/2026-10-15-mnt-250-schedule-cycle-rule.md) — Reviewed the MNT-250 ticket against `RelayTargetStateService`, found the title described shipped behaviour and two rule bullets contradicted each other, then implemented the respec: a 30-min-every-2-hours cycle rule in the schedule branch with a new `RelayMode.CYCLE` and migration 0011, leaving midseason untouched; also pinned the test module's clock, which the new time-based rule made necessary (666 passed) (2026-10-15)
- [MCP server review and project-agnostic refactor](pages/2026-10-11-mcp-server-review-agnostic-refactor.md) — Fixed two silent path bugs that made the wiki tools read another repository and the docstring index cover only the MCP server; replaced 10 cache globals with one frozen snapshot; made the server project-agnostic; later added wiki dedup/consistency, an AGENTS.md audit, and fixes for all 8 unresolved PR #41 review threads (621 passed) (2026-10-11)
- [Midseason pump cadence — 30 minutes every 2 hours](pages/2026-10-11-midseason-pump-cadence-30min.md) — Changed the midseason pump duty cycle from 1 hour every 3 hours to 30 minutes every 2 hours (6:00–6:30, 8:00–8:30, …), keeping the night guard and the always-open servo rule (98 passed) (2026-10-11)
- [Relay log consumer — review and fixes](pages/2026-09-29-relay-log-consumer-fixes.md) — Reviewed the move of relay-log creation into the Redis consumer: fixed the system-user fallback, added ON/OFF validation, updated docstrings, and migrated the tests that still called the removed `apply_target_state()` (391 passed) (2026-09-29)
- [MNT-226: Relay state log](pages/2026-09-28-mnt-226-relay-state-log.md) — Implementation of MNT-226: Relay state log (2026-09-28)
- [Boiler tile shows no temperatures — API returns override, not live status](pages/2026-09-27-boiler-live-status-api.md) — `GET /api/v1/boiler/status/` returned only override-derived setpoints, so the tile showed `—` in panel mode; the API now also returns the same live ebusd fields as `boiler_status` and the tile renders Flow/Return/Tank temps (2026-09-27)
- [Silk profiler unreachable — SPA catch-all shadows /silk/](pages/2026-09-24-silk-route-spa-catchall-shadow.md) — Local dev server was down, and `/silk/` also served the SPA `index.html` because the catch-all `re_path` didn't exclude `silk`; added `silk(?:$|/)` to the lookahead (2026-09-24)
- [Sensor relation FKs and denormalized readings](pages/2026-09-24-sensor-fks-and-denormalized-readings.md) — Migrated `SensorLog.sensor`, `Sensor.relay`, and `Sensor.linked_sensor` from char columns to nullable FKs, dropped the legacy `*_old` columns, and cached `temp`/`humidity` on `Sensor`; `is_alive` now reads `updated_at` (2026-09-24)
- [MNT-218: Split dashboard API](pages/2026-09-23-mnt-218-split-dashboard-api.md) — Split the aggregate dashboard API into per-model endpoints under `odin/api/v1/` and moved the SPA to per-tile hooks/APIs; removed the old `core/dashboard/` view, serializer, and services (2026-09-23)
- [Relay mode computed on read](pages/2026-09-23-relay-mode-compute-on-read.md) — `SERVO-BR`/`SERVO-HL` showed different modes because `mode` is a persisted snapshot; compute `mode`/`target_state` on read via `Relay.get_target_state()` in the CRUD and dashboard serializers (2026-09-23)
- [MNT-217: Relay schedule component](pages/2026-09-22-mnt-217-relay-schedule-component.md) — Added the relay schedule modal, schedule-aware relay serializers with period-overlap validation, and schedule API endpoints (2026-09-22)
- [ESP8266 relay indicators: SVG icons + mode tooltip](pages/2026-09-21-esp8266-indicator-icons.md) — Replaced `is_on`-based dots with ON/OFF SVG icons plus grey/red dots for UNKNOWN/IGNORED modes, and moved the relay `mode` into a `title` tooltip (2026-09-21)
- [MNT-215: Midseason mode](pages/2026-09-19-mnt-215-midseason-mode.md) — Introduced midseason mode with the (then) 1-hour-every-3-hours pump cadence and always-open servos; `RelayState.IGNORED` removed; cadence later superseded to 30 min every 2 h and the band gate extended by apparent temperature (2026-09-19)
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

### Relay control (state, mode, schedules, midseason/weather gate, indicators)

- [Add self-referential related_relay field to Relay](pages/2026-09-11-add-related-relay-field.md)
- [Relay state sync — admin refresh and Redis consumer](pages/2026-09-11-relay-state-redis-consumer.md)
- [Relay state/mode refactor — review, test sync, and fixes](pages/2026-09-18-relay-state-mode-refactor.md)
- [MNT-215: Midseason mode](pages/2026-09-19-mnt-215-midseason-mode.md)
- [ESP8266 relay indicators: SVG icons + mode tooltip](pages/2026-09-21-esp8266-indicator-icons.md)
- [MNT-217: Relay schedule component](pages/2026-09-22-mnt-217-relay-schedule-component.md)
- [Relay mode computed on read](pages/2026-09-23-relay-mode-compute-on-read.md)
- [MNT-226: Relay state log](pages/2026-09-28-mnt-226-relay-state-log.md)
- [Relay log consumer — review and fixes](pages/2026-09-29-relay-log-consumer-fixes.md)
- [Midseason pump cadence — 30 minutes every 2 hours](pages/2026-10-11-midseason-pump-cadence-30min.md)
- [MNT-250 spec review — schedule cycle rule](pages/2026-10-15-mnt-250-schedule-cycle-rule.md)
- [MNT-253 — Midseason humidity & wind research](pages/2026-10-22-mnt-253-midseason-humidity-wind-research.md)
- [MNT-255: Override by schedule](pages/2026-10-25-mnt-255-override-by-schedule.md) — 2026-10-25 (also covers MNT-259)
- [RelayTargetStateService review — antifreeze fail-safe and rule order](pages/2026-10-26-relay-target-state-antifreeze-review.md) — 2026-10-26

### Boiler / eBus control

- [Proterm Lynx 25 eBus Protocol Investigation](pages/2026-08-11-proterm-lynx-25-ebus-protocol.md)
- [ebusd lost its device config (boiler reads all failed) + refresh timer disabled](pages/2026-09-11-ebusd-config-load-boiler-refresh.md)
- [MNT-206: Boiler mode controller](pages/2026-09-17-mnt-206-boiler-mode-controller.md)
- [MNT-207: Wire boiler mode controller into scheduler tick / cron](pages/2026-09-18-mnt-207-wire-boiler-mode-controller-into-scheduler-tick-cron.md)
- [MNT-208: Boiler dashboard](pages/2026-09-18-mnt-208-boiler-dashboard.md)
- [Boiler tile shows no temperatures — API returns override, not live status](pages/2026-09-27-boiler-live-status-api.md)

### Dashboard API & frontend SPA

- [React frontend PR review — apply CodeRabbit + coding-guideline fixes](pages/2026-07-21-react-frontend-pr-review-fixes.md)
- [Fix React SPA dev-mode issues: docs, proxy, base path, StrictMode Loading bug](pages/2026-08-24-react-spa-dev-mode-debug.md)
- [MNT-218: Split dashboard API](pages/2026-09-23-mnt-218-split-dashboard-api.md)
- [Silk profiler unreachable — SPA catch-all shadows /silk/](pages/2026-09-24-silk-route-spa-catchall-shadow.md)

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

### MCP server & agent tooling

- [MCP server review and project-agnostic refactor](pages/2026-10-11-mcp-server-review-agnostic-refactor.md)