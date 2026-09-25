---
title: 'MNT-217: Relay schedule component'
date: '2026-09-22'
type: implementation
status: resolved
session_id: ses_f373b1709ffebFIpwpeCP82eyP
services: [SelectField, SubmitButton, TextField, Icon, Esp8266SensorsTile, RelayScheduleModal,
  relays, DashboardPage, StyleguidePage, components, serializers, views, schedule,
  test_auth, test_relays, pyproject, uv, .sessions, INDEX, 2026-09-22-mnt-217-relay-schedule-component]
branch: mnt-217-relay-schedule-component
tickets: [MNT-217]
tags: [wiki, feature, frontend, backend]
related: [2026-09-18-relay-state-mode-refactor, 2026-09-19-mnt-215-midseason-mode,
  2026-09-21-esp8266-indicator-icons]
---
# MNT-217: Relay schedule component

## TL;DR

The Relay Schedule Component implementation added a new React modal for managing relay schedules, updated relay APIs to return and accept context, and introduced validation for overlapped periods. The changes were successfully tested and documented in a new wiki page. The outcome is a functional relay schedule management system with a user-friendly interface.

---

## Overview

The implementation involved updating `odin/api/v1/relays/serializers.py` and `odin/api/v1/relays/views.py` to support schedule-aware serialization and validation, creating a new `RelayScheduleModal` component in `frontend/src/components/tile/RelayScheduleModal.tsx`, and adding API endpoints in `frontend/src/lib/api/relays.ts`. The changes also included updates to tests in `odin/tests/api/test_relays.py` and the addition of a wiki page documenting the changes.

## Changed files

- `frontend/src/components/form/SelectField.tsx` (33/0)
- `frontend/src/components/form/SubmitButton.tsx` (1/1)
- `frontend/src/components/form/TextField.tsx` (1/1)
- `frontend/src/components/icons/Icon.tsx` (1/0)
- `frontend/src/components/tile/Esp8266SensorsTile.tsx` (54/28)
- `frontend/src/components/tile/RelayScheduleModal.tsx` (357/0)
- `frontend/src/lib/api/relays.ts` (45/0)
- `frontend/src/pages/DashboardPage.tsx` (29/1)
- `frontend/src/pages/StyleguidePage.tsx` (30/0)
- `frontend/src/styles/components.css` (69/0)
- `odin/api/v1/relays/serializers.py` (61/2)
- `odin/api/v1/relays/views.py` (14/8)
- `odin/static/img/schedule.svg` (4/0)
- `odin/tests/api/test_auth.py` (6/1)
- `odin/tests/api/test_relays.py` (217/25)
- `pyproject.toml` (1/1)
- `uv.lock` (1/1)
- `wiki/.sessions.json` (2/1)
- `wiki/INDEX.md` (1/0)
- `wiki/pages/2026-09-22-mnt-217-relay-schedule-component.md` (130/0)

## Stat

```text
frontend/src/components/form/SelectField.tsx       |  33 ++

 frontend/src/components/form/SubmitButton.tsx      |   2 +-

 frontend/src/components/form/TextField.tsx         |   2 +-

 frontend/src/components/icons/Icon.tsx             |   1 +

 .../src/components/tile/Esp8266SensorsTile.tsx     |  82 +++--

 .../src/components/tile/RelayScheduleModal.tsx     | 357 +++++++++++++++++++++

 frontend/src/lib/api/relays.ts                     |  45 +++

 frontend/src/pages/DashboardPage.tsx               |  30 +-

 frontend/src/pages/StyleguidePage.tsx              |  30 ++

 frontend/src/styles/components.css                 |  69 ++++

 odin/api/v1/relays/serializers.py                  |  63 +++-

 odin/api/v1/relays/views.py                        |  22 +-

 odin/static/img/schedule.svg                       |   4 +

 odin/tests/api/test_auth.py                        |   7 +-

 odin/tests/api/test_relays.py                      | 242 ++++++++++++--

 pyproject.toml                                     |   2 +-

 uv.lock                                            |   2 +-

 wiki/.sessions.json                                |   3 +-

 wiki/INDEX.md                                      |   1 +

 .../2026-09-22-mnt-217-relay-schedule-component.md | 130 ++++++++

 20 files changed, 1057 insertions(+), 70 deletions(-)
```

## Build plan

## Implementation Plan
The implementation plan for the Relay Schedule Component (MNT-217) involves both backend and frontend changes.

### Backend Changes
1. **Update `odin/api/v1/relays/serializers.py`**:
   - Add `context = serializers.JSONField()` to `RelaySerializer`.
   - Replace `RelayUpdateContextSerializer` with schedule-aware serializers: `RelayPeriodSerializer` and `RelayScheduleSerializer`.
   - Override `validate_periods` in `RelayScheduleSerializer` to reject overlaps.

2. **Update `odin/api/v1/relays/views.py`**:
   - Remove the `state` column write in `perform_update`.
   - After context update, recompute target via `RelayTargetStateService` and publish via `RedisBus`.
   - Add type-specific validation for `target_temp` and `target_state`.

3. **Update Tests in `odin/tests/a…

## Test Results

- Session status: `resolved`
- OpenCode session id: `ses_f373b1709ffebFIpwpeCP82eyP`

---

## Follow-ups

- None

## References

- Related: [[2026-09-18-relay-state-mode-refactor]]
- Related: [[2026-09-19-mnt-215-midseason-mode]]
- Related: [[2026-09-21-esp8266-indicator-icons]]
- External: https://linear.app/mnt/issue/MNT-217/relay-schedule-component
