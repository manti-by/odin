---
title: Relay state sync — admin refresh and Redis consumer
date: 2026-09-11
type: implementation
status: resolved
session_id: ses_f6fa428f0ffeMnvUy6e1mzal4k
services: [relays, sensors, core]
branch: -
tickets: []
tags: [redis, pubsub, relays, django-admin, consumer, systemd]
related: [2026-09-11-add-related-relay-field.md, 2026-09-18-relay-state-mode-refactor.md]
---

# Relay state sync — admin refresh and Redis consumer

## TL;DR

Relay state is persisted by Coruscant under `relays:state:<relay_id>` and read on demand by
`Relay.refresh_state()`. This session wired that pull into the relay admin
(`changelist_view` / `change_view`) and extended the existing `sensor-consumer` process to
subscribe to the relay channel and refresh relays on `RELAY_STATE_UPDATE`, so state no longer
waits on the 1-minute scheduler tick. No new systemd service was needed.

## Overview

The umbrella `AGENTS.md` Redis contract says relay state is persisted under
`relays:state:<relay_id>` "so consumers can read it without a live subscription". ODIN only
ever pulled that key, and only from `build_index_context()` (scheduler, every minute) and — as
of this session — the relay admin. Coruscant additionally publishes a `RELAY_STATE_UPDATE`
envelope on every real state change, but ODIN had no subscriber that accepted it, so those
messages were dropped.

Scope of this session:

- Make the relay admin reflect the latest persisted state on page load.
- Decide whether a new systemd service is required for relay updates, and implement the chosen
  option.

The first change was a small admin hook. The second was investigated against both submodules
(see Step 2) and resolved by extending the existing `consume_sensors` command rather than
adding a fifth service.

> **Note 2026-09-25 (Consistency Agent):** the consumer command has since moved to
> `odin/apps/core/management/commands/consumer.py` (tests in `odin/tests/commands/test_consumer.py`),
> and `Relay.refresh_state()` now writes the dedicated `state` column instead of
> `Relay.context["state"]` (see [[2026-09-18-relay-state-mode-refactor]]). The `consume_sensors`
> path and context-write references below are otherwise historical.

## Step 1 — refresh relay state in the admin

**File:** `odin/apps/relays/admin.py:86`

`changelist_view` now refreshes every relay in the queryset before rendering, and
`change_view` refreshes the single object. `refresh_state()` reads the persisted key and writes
it back into `Relay.context["state"]`, so the admin always shows the Coruscant-confirmed state.

Before:

```python
def changelist_view(self, request: HttpRequest, extra_context: dict | None = None) -> TemplateResponse:
    return super().changelist_view(request, extra_context)


def change_view(
    self, request: HttpRequest, object_id: int, form_url: str = "", extra_context: dict | None = None
) -> TemplateResponse:
    return super().change_view(request, object_id, form_url, extra_context)
```

After:

```python
def changelist_view(self, request: HttpRequest, extra_context: dict | None = None) -> TemplateResponse:
    for relay in self.get_queryset(request):
        relay.refresh_state()
    return super().changelist_view(request, extra_context)


def change_view(
    self, request: HttpRequest, object_id: int, form_url: str = "", extra_context: dict | None = None
) -> TemplateResponse:
    if relay := self.get_object(request, object_id):
        relay.refresh_state()
    return super().change_view(request, object_id, form_url, extra_context)
```

## Step 2 — consume RELAY_STATE_UPDATE in the existing consumer

Investigation findings:

- Contract (umbrella `AGENTS.md`): ODIN → Coruscant control on `relays:control`; Coruscant →
  ODIN telemetry on `sensors:telemetry`; last-known relay state persisted under
  `relays:state:<id>` for pull reads.
- Coruscant's `update_relay_state()` (`coruscant/services/redis_bus.py`) persists the key, then
  publishes `RELAY_STATE_UPDATE` to `REDIS_RELAYS_CHANNEL` (`relays:control`) — i.e. the control
  channel, which is contract drift.
- ODIN's `consume_sensors` subscribed only to `sensors:telemetry` and explicitly rejected any
  non-`SENSOR_DATA_UPDATE` type, so relay acks never reached ODIN.

Options weighed: (A) extend `consume_sensors`, (B) add a new `consume_relays` command +
`relay-consumer.service`, (C) keep polling only. Option A was chosen — it avoids a fifth
service and keeps one subscriber process.

The command now subscribes to both channels and dispatches by envelope `type`. Relay messages
are treated as wake-up signals: `process_relay_message` looks the relay up and calls
`refresh_state()`, so the persisted key stays the source of truth and duplicate deliveries
(including ODIN's own control echoes on `relays:control`) are harmless. Unknown types and ids
are skipped, matching the contract's "tolerate unknown values" rule.

**File:** `odin/apps/sensors/management/commands/consume_sensors.py`

```python
channels = (settings.REDIS_SENSORS_CHANNEL, settings.REDIS_RELAYS_CHANNEL)
self.pubsub = self.client.pubsub()
self.pubsub.subscribe(*channels)
```

```python
match message.get("type"):
    case MessageType.SENSOR_DATA_UPDATE.value:
        self.process_sensor_message(message)
    case MessageType.RELAY_STATE_UPDATE.value:
        self.process_relay_message(message)
    case other:
        logger.warning(f"Skipping bus message with unexpected type {other!r}")
```

```python
def process_relay_message(self, message: dict[str, Any]) -> None:
    data = message.get("data")
    relay_id = data.get("relay_id") if isinstance(data, dict) else None
    if not relay_id:
        logger.warning("Skipping relay message with missing relay_id")
        return

    relay = Relay.objects.filter(relay_id=relay_id).first()
    if relay is None:
        logger.warning(f"Skipping relay message for unknown relay {relay_id!r}")
        return

    relay.refresh_state()
```

**File:** `configs/sensor-consumer.service:2` — description updated to
"Sensor and relay consumer for ODIN server". No new unit or `Makefile deploy` entry.

## Test Results

- `uv run ruff check` + `ruff format --check` on changed Python files — clean.
- `uv run pytest ... odin/tests/commands/test_consume_sensors.py` — 7 passed (new file covers sensor persistence, relay refresh, unknown relay, missing `relay_id`, unknown type, malformed payload, both-channel subscription).
- `uv run pytest ... odin/tests/commands odin/tests/models/test_relays.py odin/tests/admin/test_relay_admin.py` — 49 passed.

---

## Follow-ups

- Coruscant should publish relay state acks to `sensors:telemetry` (the contract's telemetry
  channel) instead of `relays:control`; needs a coruscant PR plus an umbrella gitlink bump.
  ODIN works either way now because it subscribes to both and re-reads the persisted key.
- `build_index_context()` still calls `refresh_state()` per relay (existing O(n) TODO for a
  batch refresh).
- Pre-existing uncommitted tree state (not changed this session): `Relay.target_state` switched
  to `cached_property` and empty `odin/apps/relays/management/*/__init__.py` files removed.

## References

- Related: [[2026-09-11-add-related-relay-field]]
