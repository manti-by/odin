---
title: 'MNT-267: Override schedule admin component'
date: '2026-10-27'
type: implementation
status: resolved
session_id: ses_e825f8a3affezWSHduV4eTXQ2M
services: [admin, schedule, _override_period_row, override_schedule, test_relay_admin,
  pyproject, .sessions, INDEX, 2026-10-27-mnt-267-override-schedule-admin-component]
branch: mnt-267-override-schedule-admin-component
tickets: [MNT-267]
tags: [wiki, backend, feature]
related: [2026-10-25-mnt-255-override-by-schedule.md, 2026-09-22-mnt-217-relay-schedule-component.md,
  2026-10-26-relay-target-state-antifreeze-review.md]
---

# MNT-267: Override schedule admin component

## TL;DR
This session implemented the override schedule admin component for the relay Django admin edit page. The implementation involved creating a new template, extending the existing JavaScript code, and modifying the admin model to support the override schedule component. The changes were tested, and a wiki page was added to document the implementation.

## Overview
The goal of this session was to add the ability to edit the override schedule from the relay context in the Django admin. The proposed implementation plan involved creating a new template, extending the existing JavaScript code, and modifying the admin model to support the override schedule component.

## Step 1 — Create a new template
A new template `odin/templates/admin/override_schedule.html` was created to render the override schedule component. The template mirrors the existing `schedule.html` template but with differences in input names and field sets.

## Step 2 — Extend the JavaScript code
The `odin/static/js/admin/schedule.js` file was extended to support the override schedule component. A second `DOMContentLoaded` block was added to run the same add/remove/index logic against any element with `id="override-periods-container"`.

## Step 3 — Modify the admin model
The `odin/apps/relays/admin.py` file was modified to support the override schedule component. A new display method `override_schedule` was added, and the `save_model` method was extended to collect fields named `override_schedule-periods-<index>-...` into a parallel `period_data` dict.

## Step 4 — Test the implementation
Tests were added to `odin/tests/admin/test_relay_admin.py` to test the override schedule component. The tests check that the change page renders the new component and that publishing still uses the recomputed `(state, mode)`.

## Step 5 — Add a wiki page
A new wiki page `wiki/pages/2026-10-27-mnt-267-override-schedule-admin-component.md` was added to document the implementation.

## Test Results
The tests passed, and the wiki page was added. However, there were some warnings and errors during the testing process, including a `PytestUnknownMarkWarning` and a `DeprecationWarning`.

## Follow-ups
- None

## References
- External: https://linear.app/mnt/issue/MNT-267/override-schedule-admin-component
- Related: [[2026-10-25-mnt-255-override-by-schedule]]
- Related: [[2026-09-22-mnt-217-relay-schedule-component]]
- Related: [[2026-10-26-relay-target-state-antifreeze-review]]
