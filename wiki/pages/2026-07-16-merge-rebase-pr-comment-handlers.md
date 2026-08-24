---
title: Merge/Rebase PR Comment Handlers — Not Found
date: 2026-07-16
type: investigation
status: resolved
session_id: ses_0936bf8b4ffeicx7i5kyhe8LEa
services: []
branch: -
tickets: []
tags: [github, pr, webhooks, notifications, pr-comments]
related:
  - 2026-07-16-github-pr-webhooks-search.md
  - 2026-07-16-merge-rebase-pr-comment-listener.md
---

# Merge/Rebase PR Comment Handlers — Not Found

## TL;DR

Exhaustive search for GitHub PR merge/rebase comment handlers, notification mark-as-read logic, and webhook processing found **no relevant code**. The codebase has no GitHub integration features whatsoever — the only `pull_request` reference is a GitHub Actions CI workflow trigger.

## Net effect

Any GitHub PR/webhook integration would need to be built from scratch. The existing notification system is Firebase Cloud Messaging push only, with no read-status tracking.

## Areas explored

### GitHub PR / Webhook code

Searched for `merge`, `rebase`, `pull_request`, `pr_comment`, `issue_comment`, `webhook` across all Python files in `odin/apps/`, `odin/api/`, and `odin/`. No matches.

### Notification mark-as-read

Searched for `mark_read`, `mark_as_read`, notification read-state models, and view-level read tracking. No matches.

### Notification system (existing)

- **`odin/apps/core/webpush.py`** — Sends Firebase Cloud Messaging push notifications. No read tracking.
- **`odin/apps/core/models.py`** — `Device` model for FCM subscriptions. No notification read-status field.

### Tangential matches (false positives)

| File | Match | Why irrelevant |
|---|---|---|
| `.github/workflows/checks.yml` | `pull_request:` | CI workflow trigger, not code |
| `.pre-commit-config.yaml` | `check-merge-conflict` | Pre-commit hook, not runtime |
| `odin/tests/api/test_relays.py` | "merges" in docstring | About relay schedule merging |
| `odin/tests/api/test_sensors.py` | "merges" in docstring | About sensor data merging |

## Searched

| Area | Keywords | Result |
|------|----------|--------|
| All Python/JS/HTML source | `merge`, `rebase`, `pull_request`, `pr_comment` | Only unrelated hits: migration comments, test fixture comments, AGENTS.md workflow docs |
| All source | `webhook` | No matches |
| All source | `mark_read`, `mark_as_read` | No matches |
| All source | `notification` + read state | `webpush.py` sends push notifications but no read tracking; no `Notification` model with read/unread field |
| `odin/apps/`, `odin/api/` | Any GitHub/diff/PR endpoint or handler | None |
| `.github/workflows/` | CI triggers on `pull_request` | Standard CI — not an application webhook handler |

## Existing notification surface

- **`odin/apps/core/webpush.py`** — Sends browser push notifications via WebPush/WebSocket. Fire-and-forget only; no persistence, no read/unread state.
- **`odin/static/js/sw.js`** — Service worker handling `notificationclick` / `notificationclose` for browser push notifications.
- **`odin/apps/core/models.py`** — `Device` and `Log` models only; no notification read-state model.

---

## Follow-ups

- None — this was a scoping/inventory task.

## References

- Related: [[2026-07-16-github-pr-webhooks-search]]
- Related: [[2026-07-16-merge-rebase-pr-comment-listener]]
- External: Search performed per user request to locate merge/rebase PR comment processing code.
