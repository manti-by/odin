---
title: Codebase search — GitHub/PR webhooks and notifications
date: 2026-07-16
type: investigation
status: reference
session_id: ses_0936b80f5ffeNAX9ALvMs62C4H
services: []
branch: -
tickets: []
tags: [github, webhooks, notifications, search]
related:
  - 2026-07-16-merge-rebase-pr-comment-handlers.md
  - 2026-07-16-merge-rebase-pr-comment-listener.md
---

# Codebase search — GitHub/PR webhooks and notifications

## TL;DR

Exhaustive codebase search for GitHub/PR webhook handlers, PR comment processing, merge/rebase application logic, and notification mark-as-read functionality. **No relevant files found** — Odin has no GitHub integration, PR processing, or notification read-state tracking.

---

## Net effect

The project (Odin — IoT dashboard for sensor management/weather/home-automation) does not implement any of the searched features. If these are needed, they would need to be built from scratch.

## Search scope

| Keyword | Directories searched |
|---|---|
| `merge`, `rebase`, `pull_request`, `pr_comment`, `webhook` | `odin/apps/`, `odin/api/`, `odin/services/` |
| `mark_read`, `mark_as_read`, `notification` | `odin/apps/`, `odin/api/`, `odin/static/js/` |
| `github`, `pull request`, `pr` (app code) | Whole project |

## What was ruled out

- **`.github/workflows/checks.yml`** — CI workflow that triggers on `pull_request` events, but runs Django checks/tests. Not an application webhook handler.
- **`odin/apps/core/webpush.py`** — Browser push notification via WebPush/WebSocket. No GitHub notifications or read/unread state.
- **`odin/static/js/sw.js`** — Service worker for `notificationclick`/`notificationclose` on browser push. Not related to PRs or mark-as-read.
- **Event model** — The `Log` model in `core/models.py` stores raw events but has no read-state field.

---

## Follow-ups

- If GitHub webhook integration is desired, a new endpoint (e.g. `/api/v1/webhooks/github/`) plus signature verification logic would be needed.
- If notification read-tracking is needed, a `Notification` model with `is_read` and a read-receipt API would need to be added.

## References

- Related: [[2026-07-16-merge-rebase-pr-comment-handlers]] — sibling investigations from a related session
- Related: [[2026-07-16-merge-rebase-pr-comment-listener]] — sibling investigations from a related session
- External: None
