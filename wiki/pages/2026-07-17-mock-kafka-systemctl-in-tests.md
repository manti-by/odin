---
title: Mock Kafka and systemctl in dashboard tests for CI
date: 2026-07-17
type: implementation
status: resolved
session_id: ses_090b6cef1ffeZJhabRdjqA2WRX
services: [main]
branch: -
tickets: []
tags: [testing, ci, kafka, mocking]
related: [2026-07-21-react-frontend-pr-review-fixes.md]
---

# Mock Kafka and systemctl in dashboard tests for CI

## TL;DR

Dashboard tests fail in CI / macOS because `KafkaService.get_relay_data()` tries to connect to Kafka (not available) and `systemd_status()` calls `/usr/bin/systemctl` (not available). Both are mocked in `test_dashboard.py` — `systemd_status` at the class level via `setup_method`, Kafka per test where needed. All 9 dashboard tests pass after the fix.

---

## Overview

GitHub Actions and dev machines (macOS) don't have Kafka brokers or `systemctl`. The dashboard view's `build_index_context` calls both `systemd_status` and `KafkaService.get_relay_data` (through the relay's `refresh_state_from_kafka`), so every dashboard test blows up with either `NoBrokersAvailable` or `FileNotFoundError` for `/usr/bin/systemctl`.

Fix: add `unittest.mock.patch` to the test class.

## Step 1 — Mock `systemd_status` at the class level

`build_index_context` calls `systemd_status(service)` which runs `subprocess.run(["/usr/bin/systemctl", ...])`. Every dashboard test triggers this, so the mock is applied in `setup_method` and torn down in `teardown_method`.

**File:** `odin/tests/views/test_dashboard.py` — `setup_method`

**Before:** no mocking → `FileNotFoundError` on non-Linux.
**After:** `setup_method` patches `odin.apps.core.services.systemd_status` → returns a canned dict `{"active": "active", ...}`.

## Step 2 — Mock `KafkaService.get_relay_data` per test

`test_dashboard__sensor_relay_and_linked_sensor` is the only test that exercises a relay with Kafka state refresh.

**File:** `odin/tests/views/test_dashboard.py` — `test_dashboard__sensor_relay_and_linked_sensor`

**Before:** `KafkaService.get_relay_data` → `KafkaConsumer(...)` → `NoBrokersAvailable`.
**After:** patched to return `{"state": "ON"}`.

## Test Results

```text
9 passed in test_dashboard.py        ✓
Full suite: 7 failed → 0 failed     ✓
```

---

## Follow-ups

- None

## References

- Related: [[2026-07-21-react-frontend-pr-review-fixes]]
