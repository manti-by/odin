---
title: Fix type errors and verify CI flow
date: 2026-07-16
type: implementation
status: resolved
session_id: ses_0962f911dffeNV7Q0xyksdxnmJ
services: [core, sensors, relays, currency]
branch: -
tickets: []
tags: [typing, ci, type-checking]
related: [2026-07-16-sensor-model-queryset-manager.md]
---

# Fix type errors and verify CI flow

## TL;DR

Fixed 9 `ty` type errors across 5 files, patched 2 test stubs broken under
`DEBUG=False`, and ran `make ci` to 193/193 green. PostgreSQL and Redis are
required locally; the `.env` file must be sourced for test settings to apply.

---

## Overview

`ty check` exposed 9 type errors in the codebase. These were fixed across 5 files:
sensor models (QuerySet return types), core admin (unused ignore comment),
currency services (DateField type inference), and a relay migration (invalid
annotations). After fixing, `ty check` passed cleanly and `make ci` was run
end-to-end.

Three rounds of CI:
1. **No PostgreSQL** — `psycopg2.OperationalError`, tests wouldn't even start.
2. **PostgreSQL configured** — 185/193 passed; 8 env-only failures (Redis, systemctl).
3. **After sourcing .env + fixing test stubs** — 193/193 green.

Two tests failed under `DEBUG=False` because they asserted on `subprocess.run`
call-counts that only matched the debug path; patched the mocks to account
for the release path. The remaining 6 Redis/systemctl failures resolved once
Redis was started locally and `.env` was sourced.

## Fix 1 & 2 — SensorQuerySet / SensorManager return types

**File:** odin/apps/sensors/models.py

Changed `QuerySet[Sensor]` return annotations to `Self` on filter methods
(`ds18b20()`, `esp8266()`, `visible()`, `all_with_relations()`) so method
chaining is properly typed. Added `SensorQuerySet` return type on
`SensorManager` proxies.

## Fix 3 — Unused type: ignore

**File:** odin/apps/core/admin.py

Removed stale `# ty: ignore[invalid-assignment]` that suppressed nothing.

## Fix 4 — DateField type inference

**File:** odin/apps/currency/services.py

Wrapped `date` access in `cast(date, ...)` to resolve Django `DateField` vs
Python `date` type mismatch.

## Fix 5 — Invalid type annotations in migration

**File:** odin/apps/relays/migrations/0005_convert_schedule_to_periodic.py

Removed `: float` annotations on dict subscript assignments (lines 44, 57)
which are not valid Python syntax in that context.

## CI Results

| Step       | Status | Detail |
|------------|--------|--------|
| install    | ✅     | `uv sync` passed |
| check      | ✅     | `ty check` + pre-commit clean |
| django     | ✅     | migrations + system check |
| full-test  | ✅     | 193/193 passed (after 3 rounds) |

Round 3 details:
- **2 test stubs fixed** — `test_core_admin` and `test_check_swap` were missing
  `subprocess.run` mocks for the `DEBUG=False` release path.
- **6 Redis/systemctl tests** — resolved once Redis was running locally and
  `.env` was sourced.

---

## Follow-ups

- None — all type errors fixed and `make ci` is 193/193 green.

## References

- Related: [[2026-07-16-sensor-model-queryset-manager]]
