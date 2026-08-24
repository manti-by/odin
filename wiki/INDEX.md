# odin Wiki — Index

Session knowledge base for the odin project - one Markdown page per debugging
chase, investigation, code review, or set of changes. See [README.md](README.md) for conventions
and [TEMPLATE.md](TEMPLATE.md) for the page template. New pages are added and updated automatically
by the plugin.

## Pages

_Newest first._

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

### Type checking & CI flow

- [Fix type errors and verify CI flow](pages/2026-07-16-fix-type-errors-ci-flow.md)
- [Mock Kafka and systemctl in dashboard tests for CI](pages/2026-07-17-mock-kafka-systemctl-in-tests.md)

### React frontend migration review

- [React frontend PR review — apply CodeRabbit + coding-guideline fixes](pages/2026-07-21-react-frontend-pr-review-fixes.md)
- [Fix React SPA dev-mode issues: docs, proxy, base path, StrictMode Loading bug](pages/2026-08-24-react-spa-dev-mode-debug.md)

_Also belongs to "Type checking & CI flow" (wired frontend checks into Makefile/CI)._

### Sensor data model

- [Sensor Model QuerySet and Manager Investigation](pages/2026-07-16-sensor-model-queryset-manager.md)

### Boiler eBus control

- [Proterm Lynx 25 eBus Protocol Investigation](pages/2026-08-11-proterm-lynx-25-ebus-protocol.md)
