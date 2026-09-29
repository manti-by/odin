---
title: 'Relay log consumer — review and fixes'
date: '2026-09-29'
type: implementation
status: resolved
session_id: ses_f1143dabfffezAT7zzbJ4n8yci
services: [consumer, redis_bus, relays-admin, relays-models, settings, test_consumer,
  test_redis_bus, test_relay_admin, test_relay_log, test_relays]
branch: master
tickets: []
tags: [relay, consumer, redis, code-review, tests]
related: [2026-09-28-mnt-226-relay-state-log, 2026-09-23-relay-mode-compute-on-read,
  2026-09-11-relay-state-redis-consumer]
---
# Relay log consumer — review and fixes

## TL;DR

Reviewed the uncommitted change that moved relay-log creation from a synchronous
`Relay.apply_target_state()` write path into the Redis consumer, found six bugs, and
fixed the five that were in scope. The consumer now validates the incoming `state`
(ON/OFF only), attributes the log to `user_id` with a working system-user fallback, and
writes the audit row after persisting `state`. Updated every affected test plus the
orphaned model tests that still called the removed method. `391 passed`, ruff and `ty`
clean.

---

## Overview

MNT-226 introduced `RelayLog`/`RelayLogService` ([[2026-09-28-mnt-226-relay-state-log]]).
A follow-up change in the working tree rewired *where* relay logs are produced:

- `Relay.apply_target_state()` was deleted from `odin/apps/relays/models.py`.
- The admin `save_model` no longer computes/persists/logs; it only publishes to Redis.
- `RedisBus.publish_relay_control()` gained a `user` kwarg and now sends `user_id` in the envelope.
- The consumer `process_relay_message` now writes `state` and creates the `RelayLog`.

This page records the review findings and the applied fixes. Admin's move to async logging
(finding 4) is **intended** and was left unchanged, per the author.

## Findings

### 1. Broken system-user fallback — High

**File:** `odin/apps/core/management/commands/consumer.py:141`

`data.get("user_id", settings.REDIS_BUS_USER_ID)` never fell back: `publish_relay_control`
always emits an explicit `"user_id": None` for system updates, so `.get()` returns `None`
rather than the default. Automatic updates were logged with `updated_by=None`. The lookup
also used `.last()` and passed the raw JSON pk unvalidated.

**Fix:** `data.get("user_id") or settings.REDIS_BUS_USER_ID` with `.first()`.

### 2. Unvalidated write, no atomicity — High

**File:** `odin/apps/core/management/commands/consumer.py:138-139`

The envelope `state` was written to `relay.state` with no `RelayState` validation, and the
`save()` + `log_change()` pair had no transaction, so a crash between them left state
without an audit row.

**Fix:** validate `state in (ON, OFF)` and skip otherwise. Transaction intentionally **not**
added (author's call).

### 3. Stale docstring — Low

**File:** `odin/apps/core/management/commands/consumer.py:111`

`process_relay_message` still described the old "refresh from persisted Redis key" behavior.

**Fix:** docstring rewritten to describe apply-and-audit.

### 4. Admin no longer persists/logs synchronously — Intended, not changed

**File:** `odin/apps/relays/admin.py:97-136`

After the change, `save_model` only publishes `obj.target_state`; `state`/`mode` updates
and the `RelayLog` row now depend on the async consumer round-trip. If Redis is unreachable,
`force_state`/`context` is saved but `state`/`mode` never update and nothing is logged.
Author confirmed this is intended. Dead leftovers from the removal (unused `before`
snapshot and `RelayLogService` import) were cleaned up — no behavior change.

### 5. Contract test broke on the new envelope — Medium

**File:** `odin/apps/core/redis_bus.py:114`

`data` is now `{relay_id, state, user_id}`, breaking the exact-dict assert in
`odin/tests/services/test_redis_bus.py`. It also assumed `User`; an `AnonymousUser` passes
`if user` but yields `pk=None`.

**Fix:** test updated for the new shape plus a user-attribution case. Note the home-level
`AGENTS.md` Redis contract still documents `relays:control` as `{relay_id, state}`.

### 6. Setting type + orphaned references — Low

**File:** `odin/settings/base.py:313`

`os.getenv("REDIS_BUS_USER_ID", 2)` returns `str` when the env var is set and `int` otherwise.
The deletion of `apply_target_state()` also left stale references: the `refresh_state`
docstring, dead imports in `models.py`, and ~40 model tests still calling the method.

**Fix:** wrap in `int(...)`, update docstrings, remove dead imports, and migrate the tests.

## Fixes applied

### Step 1 — Consumer: validation, fallback, docstring

**File:** `odin/apps/core/management/commands/consumer.py`

```python
if (state := data.get("state")) not in (RelayState.ON, RelayState.OFF):
    logger.warning(f"Skipping relay message with invalid state {state!r} for relay {relay_id!r}")
    return

before = RelayLogService.snapshot(relay)
relay.state = state
relay.save(update_fields=["state", "updated_at"])

user = User.objects.filter(pk=data.get("user_id") or settings.REDIS_BUS_USER_ID).first()
if not RelayLogService(relay, user=user).log_change(before):
    logger.error(f"Relay log does not created for {relay_id!r}")
```

### Step 2 — Settings int cast

**File:** `odin/settings/base.py:313`

```python
REDIS_BUS_USER_ID = int(os.getenv("REDIS_BUS_USER_ID", 2))
```

### Step 3 — Docstrings + dead-code cleanup

- `odin/apps/relays/models.py` — `refresh_state` docstring now points at "API update,
  consumer relay message handling"; dropped now-unused `Any`, `transaction`, `User` imports.
- `odin/apps/core/redis_bus.py` — `publish_relay_control` docstring documents `user_id`.
- `odin/apps/relays/admin.py` — removed the dead `before` snapshot block and the unused
  `RelayLogService` import (behavior unchanged; async logging is intended).

### Step 4 — Test migration

- `odin/tests/models/test_relays.py` — 37 call sites of the removed `apply_target_state()`
  rewritten to the read-only API:

  ```python
  state, mode = relay.get_target_state()
  assert state == RelayState.ON
  assert mode == RelayMode.BASIC
  ```

- `odin/tests/commands/test_consumer.py` — replaced the two `get_relay_latest_message`
  mock tests with apply-and-audit tests: log created, `updated_by` from `user_id`, system
  fallback, unknown relay, invalid/missing state. Added a `_relay_message` helper.
- `odin/tests/services/test_redis_bus.py` — envelope assert includes `user_id`; added a
  user-attribution test.
- `odin/tests/admin/test_relay_admin.py` — publish call now asserted with `user=None`.
- `odin/tests/services/test_relay_log.py` — dropped the three `apply_target_state` tests,
  kept the pure-property test as `TestRelayTargetState`, and rewrote the admin tests to
  assert publish-only / no synchronous log.

## Test Results

- `uv run pytest odin/` — **391 passed**
- `uv run ruff check odin/` — clean; `ruff format --check` — 223 files already formatted
- `uv run ty check` — all checks passed
- `bandit` not installed in the venv (pre-commit manages its own env)

## Changed files

- `odin/apps/core/management/commands/consumer.py`
- `odin/apps/relays/models.py`
- `odin/apps/relays/admin.py`
- `odin/apps/core/redis_bus.py`
- `odin/settings/base.py`
- `odin/tests/models/test_relays.py`
- `odin/tests/commands/test_consumer.py`
- `odin/tests/services/test_redis_bus.py`
- `odin/tests/admin/test_relay_admin.py`
- `odin/tests/services/test_relay_log.py`

---

## Follow-ups

- Log message `"Relay log does not created for ..."` is ungrammatical (left as-is).
- Home-level `AGENTS.md` Redis contract for `relays:control` omits `user_id`.
- Admin async logging: if Redis is down, `state`/`mode` update and the audit row are skipped
  (intended, but worth a documented degradation note).

## References

- Related: [[2026-09-28-mnt-226-relay-state-log]]
- Related: [[2026-09-23-relay-mode-compute-on-read]]
- Related: [[2026-09-11-relay-state-redis-consumer]]
