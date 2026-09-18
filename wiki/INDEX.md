# odin Wiki — Index

Session knowledge base for the odin project - one Markdown page per debugging
chase, investigation, code review, or set of changes. See [README.md](README.md) for conventions
and [TEMPLATE.md](TEMPLATE.md) for the page template. New pages are added and updated automatically
by the plugin.

## Pages

_Newest first._

- [MNT-208: Boiler dashboard](pages/2026-09-18-mnt-208-boiler-dashboard.md) — Implementation of MNT-208: Boiler dashboard (2026-09-18)
- [Relay state/mode refactor — review, test sync, and fixes](pages/2026-09-18-relay-state-mode-refactor.md) — Reviewed the relay `state`/`mode` column refactor (29 broken tests), synced the suite to the single-value `target_state`, fixed API update not populating the `state` column and API reads overwriting actual state with the computed target; 259 tests green (2026-09-18)
- [ebusd lost its device config + refresh timer disabled](pages/2026-09-11-ebusd-config-load-boiler-refresh.md) — Boiler writes worked but reads all returned `element not found`: the long-running ebusd lost outbound HTTPS for a week+ (no Vaillant config loaded) and `boiler-refresh.timer` was disabled; fixed via restart, `--scanconfig=08`, and enabling the timer (2026-09-11)
- [Relay state sync — admin refresh and Redis consumer](pages/2026-09-11-relay-state-redis-consumer.md) — Refreshed relay state on admin list/detail load and extended `consume_sensors` to also subscribe to `relays:control`, refreshing relays on `RELAY_STATE_UPDATE`; no new systemd service needed (2026-09-11)
- [Add self-referential related_relay field to Relay](pages/2026-09-11-add-related-relay-field.md) — Added a nullable self-FK `related_relay` + migration 0006 and surfaced it in the relay admin as a select dropdown; groundwork for the servo→pump TODO (2026-09-11)
- [Fix React SPA dev-mode issues: docs, proxy, base path, StrictMode Loading bug](pages/2026-08-24-react-spa-dev-mode-debug.md) — Synced docs with the React SPA migration; fixed Vite `base: "/static/"` redirecting dev `/` → `/static/` 404; removed broken `isMountedRef` in `useDashboardData` so tiles load data under StrictMode (2026-08-24)
- [Proterm Lynx 25 eBus Protocol Investigation](pages/2026-08-11-proterm-lynx-25-ebus-protocol.md) —
  eBus protocol investigation of the Vaillant BAI boiler: reads mapped; the 2026-08-11 write
  failures were traced to malformed `SetMode` frames (NN=07, missing leading submessage ID), and
  correctly framed writes via `boiler-set`/ebusd work — pairing-window theory superseded (2026-08-11).
- [React frontend PR review — apply CodeRabbit + coding-guideline fixes](pages/2026-07-21-react-frontend-pr-review-fixes.md) — Reviewed epic/react_frontend vs master and PR #14's CodeRabbit comments; applied all non-security fixes plus coding-guideline violations, wired frontend checks into CI/Makefile (2026-07-21)
- [Mock Kafka and systemctl in dashboard tests for CI](pages/2026-07-17-mock-kafka-systemctl-in-tests.md) — Mocked KafkaService and systemd_status in dashboard tests to prevent NoBrokersAvailable and FileNotFoundError on CI/non-Linux (2026-07-17)
- [Codebase search — GitHub/PR webhooks and notifications](pages/2026-07-16-github-pr-webhooks-search.md) — Exhaustive search found no GitHub integration, PR processing, or notification mark-as-read logic in the codebase (2026-07-16)
- [Sensor Model QuerySet and Manager Investigation](pages/2026-07-16-sensor-model-queryset-manager.md) — Investigation of Sensor model, SensorQuerySet, SensorManager, and SensorLogManager in sensors/models.py (2026-07-16)
- [Fix type errors and verify CI flow](pages/2026-07-16-fix-type-errors-ci-flow.md) — Fixed 9 ty type errors, patched 2 test stubs, and ran make ci to 193/193 green (2026-07-16)
- [Merge/Rebase PR Comment Handlers — Not Found](pages/2026-07-16-merge-rebase-pr-comment-handlers.md) — Exhaustive search found no GitHub PR/webhook or notification mark-as-read code in the project (2026-07-16)
- [PR merge/rebase comment listener marks as read despite errors](pages/2026-07-16-merge-rebase-pr-comment-listener.md) — Debug notes on a listener that marks notifications read despite errors; verified 2026-08-24 that no such code exists in odin — kept as reference (2026-07-16)

## By topic

_Topic clusters maintained by the Consistency Agent; topics with the most pages first._

### GitHub integration & notifications

- [Codebase search — GitHub/PR webhooks and notifications](pages/2026-07-16-github-pr-webhooks-search.md)
- [Merge/Rebase PR Comment Handlers — Not Found](pages/2026-07-16-merge-rebase-pr-comment-handlers.md)
- [PR merge/rebase comment listener marks as read despite errors](pages/2026-07-16-merge-rebase-pr-comment-listener.md)
- [MNT-206: Boiler mode controller](pages/2026-09-17-mnt-206-boiler-mode-controller.md) — 2026-09-17
- [MNT-207: Wire boiler mode controller into scheduler tick / cron](pages/2026-09-18-mnt-207-wire-boiler-mode-controller-into-scheduler-tick-cron.md) — 2026-09-18

### Type checking & CI flow

- [Fix type errors and verify CI flow](pages/2026-07-16-fix-type-errors-ci-flow.md)
- [Mock Kafka and systemctl in dashboard tests for CI](pages/2026-07-17-mock-kafka-systemctl-in-tests.md)

### React frontend migration review

- [React frontend PR review — apply CodeRabbit + coding-guideline fixes](pages/2026-07-21-react-frontend-pr-review-fixes.md)
- [Fix React SPA dev-mode issues: docs, proxy, base path, StrictMode Loading bug](pages/2026-08-24-react-spa-dev-mode-debug.md)

_Also belongs to "Type checking & CI flow" (wired frontend checks into Makefile/CI)._
- [MNT-208: Boiler dashboard](pages/2026-09-18-mnt-208-boiler-dashboard.md) — 2026-09-18

### Sensor data model

- [Sensor Model QuerySet and Manager Investigation](pages/2026-07-16-sensor-model-queryset-manager.md)

### Boiler eBus control

- [ebusd lost its device config + refresh timer disabled](pages/2026-09-11-ebusd-config-load-boiler-refresh.md)
- [Proterm Lynx 25 eBus Protocol Investigation](pages/2026-08-11-proterm-lynx-25-ebus-protocol.md)