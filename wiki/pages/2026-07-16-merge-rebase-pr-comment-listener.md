---
title: PR merge/rebase comment listener marks as read despite errors
date: 2026-07-16
type: debug
status: open
session_id: ses_0936c0b3bffeYCA4iZd2LjmKSn
services: []
branch: -
tickets: []
tags: [github, pr, notifications, merge, rebase]
related: []
---

# PR merge/rebase comment listener marks as read despite errors

## TL;DR

The merge/rebase PR comment listener unconditionally marks notifications as read even when processing errors or returning empty results. This defeats the purpose of the listener by silently dropping notifications. No fix was implemented in this session.

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

- (none)