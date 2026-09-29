---
title: 'MNT-226: Relay state log'
date: '2026-09-28'
type: implementation
status: resolved
session_id: ses_f16739d48ffen6HyahSVMY3X25
services: [views, admin, 0010_relaylog, models, services, test_sensors_dashboard,
  test_consumer, test_relays, test_relay_log, pyproject, uv, INDEX, 2026-09-28-mnt-226-relay-state-log]
branch: mnt-226-relay-state-log
tickets: [MNT-226]
tags: [wiki, feature, backend]
related: [2026-09-18-relay-state-mode-refactor, 2026-09-23-relay-mode-compute-on-read,
  2026-09-11-relay-state-redis-consumer]
---
# MNT-226: Relay state log

## TL;DR

The relay state log feature has been implemented, allowing for the tracking of changes to relay state, mode, and force state. A new RelayLog model and RelayLogService have been added to store and manage these changes. The implementation includes tests and a new migration, and all tests have passed. A wiki page has been added to document the changes.

---

## Overview

A new RelayLog model has been added to odin/apps/relays/models.py to store changes to relay state, mode, and force state. The RelayLogService class in odin/apps/relays/services.py creates a new RelayLog entry when any tracked field changes. Explicit calls to the RelayLogService have been added in various locations, including odin/api/v1/relays/views.py and odin/apps/relays/admin.py. Tests have been added to odin/tests/services/test_relay_log.py to cover the new functionality.

## Changed files

- `odin/api/v1/relays/views.py` (7/2)
- `odin/apps/relays/admin.py` (19/1)
- `odin/apps/relays/migrations/0010_relaylog.py` (130/0)
- `odin/apps/relays/models.py` (92/7)
- `odin/apps/relays/services.py` (49/2)
- `odin/tests/api/test_sensors_dashboard.py` (13/0)
- `odin/tests/commands/test_consumer.py` (19/0)
- `odin/tests/models/test_relays.py` (37/37)
- `odin/tests/services/test_relay_log.py` (274/0)
- `pyproject.toml` (1/1)
- `uv.lock` (2/2)
- `wiki/INDEX.md` (2/0)
- `wiki/pages/2026-09-28-mnt-226-relay-state-log.md` (198/0)

## Stat

```text
odin/api/v1/relays/views.py                      |   9 +-

 odin/apps/relays/admin.py                        |  20 +-

 odin/apps/relays/migrations/0010_relaylog.py     | 130 +++++++++++

 odin/apps/relays/models.py                       |  99 +++++++-

 odin/apps/relays/services.py                     |  51 ++++-

 odin/tests/api/test_sensors_dashboard.py         |  13 ++

 odin/tests/commands/test_consumer.py             |  19 ++

 odin/tests/models/test_relays.py                 |  74 +++---

 odin/tests/services/test_relay_log.py            | 274 +++++++++++++++++++++++

 pyproject.toml                                   |   2 +-

 uv.lock                                          |   4 +-

 wiki/INDEX.md                                    |   2 +

 wiki/pages/2026-09-28-mnt-226-relay-state-log.md | 198 ++++++++++++++++

 13 files changed, 843 insertions(+), 52 deletions(-)
```

## Build plan

## Implementation Plan
### Step 1: Add RelayLog Model
Create a new `RelayLog` model in `odin/apps/relays/models.py` with the following fields:
- `relay`: ForeignKey to `Relay`
- `old_state`, `new_state`: nullable CharField with `RelayState.choices`
- `old_mode`, `new_mode`: nullable CharField with `RelayMode.choices`
- `old_force_state`, `new_force_state`: nullable CharField with `RelayState.active_choices()`
- `old_context`, `new_context`: nullable JSONField
- `updated_by`: nullable ForeignKey to `AUTH_USER_MODEL`
- `updated_at`, `created_at`: DateTimeField

### Step 2: Add RelayLogService
Create a `RelayLogService` class in `odin/apps/relays/services.py` with a `log_change` method to create a `RelayLog` row when at least one tracked field changes.

### Step 3: Wire Explicit Calls
Call `R…

## Test Results

- Session status: `resolved`
- OpenCode session id: `ses_f16739d48ffen6HyahSVMY3X25`

---

## Follow-ups

- None

## References

- External: https://linear.app/mnt/issue/MNT-226/relay-state-log
