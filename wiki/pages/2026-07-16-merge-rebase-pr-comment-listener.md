---
title: PR merge/rebase comment listener marks as read despite errors
date: 2026-07-16
type: debug
status: reference
session_id: ses_0936c0b3bffeYCA4iZd2LjmKSn
services: []
branch: -
tickets: []
tags: [github, pr, notifications, merge, rebase]
related:
  - 2026-07-16-github-pr-webhooks-search.md
  - 2026-07-16-merge-rebase-pr-comment-handlers.md
---

# PR merge/rebase comment listener marks as read despite errors

## TL;DR

The merge/rebase PR comment listener unconditionally marks notifications as read even when processing errors or returning empty results. This defeats the purpose of the listener by silently dropping notifications. No fix was implemented in this session.

> **Note 2026-08-24 (Consistency Agent):** verified against the current codebase
> (`rg 'mark_as_read|mark_read|webhook|pull_request'` over all Python) that no
> such listener or notification read-state code exists anywhere in odin. The two
> same-day investigations below reached the same conclusion independently, so
> this page describes a component outside the odin codebase; kept for
> reference, `status` changed from `open` (no fix is owed here).

---

## Symptom

The listener always marks the notification as read after running, regardless of whether the operation succeeded, failed, or found nothing actionable.

## Root cause

The `mark_as_read` call runs unconditionally after every attempt without checking the result or error state.

## Resolution / Fix

Not implemented. The fix should gate the `mark_as_read` call behind a success condition — only invoke it when the operation actually did meaningful work.

---

## Follow-ups

- Implement the fix: check result/error state before marking as read.
- Test with error, empty, and success scenarios.

## References

- Related: [[2026-07-16-github-pr-webhooks-search]]
- Related: [[2026-07-16-merge-rebase-pr-comment-handlers]]