---
title: Add self-referential related_relay field to Relay
date: 2026-09-11
type: implementation
status: resolved
session_id: ses_f6ffdf675ffeR7UYywCIVhc4Er
services: [main]
branch: -
tickets: []
tags: [relays, django-admin, migrations]
related: []
---

# Add self-referential related_relay field to Relay

## TL;DR

Added a nullable self-referential `related_relay` foreign key to `Relay`, generated
migration `0006_relay_related_relay`, and surfaced the field in `RelayAdmin` so the
change form renders a dropdown for picking another relay. This is groundwork for the
existing `# TODO: Get related pump state` in `RelayTargetStateService` — a servo can
now be linked to its controlling pump.

---

## Overview

The relay admin previously had no way to associate one relay with another, yet the
in-progress `RelayTargetStateService.get_servo_target_state()` already carries a
`# TODO: Get related pump state` comment. The chosen model is a nullable self-FK
(many relays may point at the same relay), with `on_delete=SET_NULL` so deleting the
target does not cascade to dependents.

## Step 1 — Model field

**File:** `odin/apps/relays/models.py:64`

```python
related_relay: models.ForeignKey[Relay] | None = models.ForeignKey(
    "self",
    null=True,
    blank=True,
    on_delete=models.SET_NULL,
    related_name="related_relays",
    verbose_name=_("Related relay"),
)
```

- `null=True, blank=True` — link is optional.
- `related_name="related_relays"` — reverse accessor for "which relays point at me".
- Annotation stays unquoted (ruff `UP037`) because the module uses
  `from __future__ import annotations`.

## Step 2 — Migration

**File:** `odin/apps/relays/migrations/0006_relay_related_relay.py`

Generated with `uv run manage.py makemigrations relays --settings=odin.settings.sqlite`.
A single `AddField`; safe on live data because the column is nullable.

## Step 3 — Django admin

**File:** `odin/apps/relays/admin.py:30`

Added `"related_relay"` to `RelayAdmin.fields`, between `is_active` and `sensor`. A
nullable FK renders as the default Django `<select>` of all relays — no custom widget
or `autocomplete_fields` needed for the current relay count.

## Test Results

- `uv run ruff check odin/apps/relays/` — passed.
- `uv run manage.py makemigrations --dry-run --check --settings=odin.settings.sqlite` — no changes detected.
- `uv run manage.py check --fail-level WARNING --settings=odin.settings.sqlite` — no issues.
- Relay test suites have 18 pre-existing failures caused by uncommitted WIP in
  `odin/apps/relays/services.py` (weather/`target_state` logic), present before this
  change. Verified by stashing all working-tree changes: `test_relays.py` is 26/26 green
  without the WIP, so the new field introduces no regressions.

---

## Follow-ups

- Resolve `RelayTargetStateService.get_servo_target_state()`'s `# TODO: Get related pump
  state` using `self.relay.related_relay.state` (return `OFF` when the related pump is off).
- Optionally expose `related_relay` through the relays API serializer
  (`odin/api/v1/relays/serializers.py`).
- Fix or land the uncommitted `services.py` WIP that currently reddens the relay tests.

## References

- Files: `odin/apps/relays/models.py`, `odin/apps/relays/admin.py`,
  `odin/apps/relays/migrations/0006_relay_related_relay.py`
