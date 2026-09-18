---
title: 'MNT-208: Boiler dashboard'
date: '2026-09-18'
type: implementation
status: resolved
session_id: ses_f4b56ab55ffeECmuDC8xiKVJm9
services: [BoilerTile, useBoilerStatus, boiler, DashboardPage, tiles, __init__, serializers,
  urls, views, mode, schedule, status, test_boiler, test_boiler_mode_controller, pyproject,
  uv]
branch: mnt-208-boiler-dashboard
tickets: [MNT-208]
tags: [wiki, frontend, feature]
related: []
---
# MNT-208: Boiler dashboard

## TL;DR

The boiler dashboard now displays the current boiler mode, override state, and weekly boil schedule. A new API endpoint was created to fetch this data, and the frontend was updated to display it. The implementation includes error handling and respects session/CSRF requirements.

---

## Overview

A new tile was added to the dashboard, mirroring existing boiler/relay tiles, to show the current boiler mode, target temperature, and next weekly boil schedule. The frontend fetches data from the new `GET /api/v1/boiler/status/` endpoint, which returns mode, override, and next boil cron information. Changes were made to files such as `frontend/src/components/tile/BoilerTile.tsx`, `odin/api/v1/boiler/serializers.py`, and `odin/api/v1/boiler/views.py`.

## Changed files

- `frontend/src/components/tile/BoilerTile.tsx` (96/0)
- `frontend/src/hooks/useBoilerStatus.ts` (50/0)
- `frontend/src/lib/api/boiler.ts` (18/0)
- `frontend/src/pages/DashboardPage.tsx` (4/0)
- `frontend/src/styles/tiles.css` (94/0)
- `odin/api/v1/boiler/__init__.py` (0/0)
- `odin/api/v1/boiler/serializers.py` (14/0)
- `odin/api/v1/boiler/urls.py` (11/0)
- `odin/api/v1/boiler/views.py` (32/0)
- `odin/api/v1/urls.py` (1/0)
- `odin/apps/boiler/services/__init__.py` (15/2)
- `odin/apps/boiler/services/mode.py` (20/0)
- `odin/apps/boiler/services/schedule.py` (27/0)
- `odin/apps/boiler/services/status.py` (34/0)
- `odin/tests/api/test_boiler.py` (72/0)
- `odin/tests/services/test_boiler_mode_controller.py` (32/0)
- `pyproject.toml` (1/1)
- `uv.lock` (1/1)

## Stat

```text
frontend/src/components/tile/BoilerTile.tsx        | 96 ++++++++++++++++++++++

 frontend/src/hooks/useBoilerStatus.ts              | 50 +++++++++++

 frontend/src/lib/api/boiler.ts                     | 18 ++++

 frontend/src/pages/DashboardPage.tsx               |  4 +

 frontend/src/styles/tiles.css                      | 94 +++++++++++++++++++++

 odin/api/v1/boiler/__init__.py                     |  0

 odin/api/v1/boiler/serializers.py                  | 14 ++++

 odin/api/v1/boiler/urls.py                         | 11 +++

 odin/api/v1/boiler/views.py                        | 32 ++++++++

 odin/api/v1/urls.py                                |  1 +

 odin/apps/boiler/services/__init__.py              | 17 +++-

 odin/apps/boiler/services/mode.py                  | 20 +++++

 odin/apps/boiler/services/schedule.py              | 27 ++++++

 odin/apps/boiler/services/status.py                | 34 ++++++++

 odin/tests/api/test_boiler.py                      | 72 ++++++++++++++++

 odin/tests/services/test_boiler_mode_controller.py | 32 ++++++++

 pyproject.toml                                     |  2 +-

 uv.lock                                            |  2 +-

 18 files changed, 522 insertions(+), 4 deletions(-)
```

## Build plan

## Implementation Plan
### Summary
The implementation plan involves adding a `Boiler` dashboard tile that displays the current boiler mode, override flag, target flow temperature, last `BoilerService` call timestamp, and the next weekly boil schedule. This will be achieved by creating a new API endpoint `GET /api/v1/boiler/status/` and updating the frontend to fetch and display the data.

### Backend
The backend changes include:
* Creating a new app namespace `odin/api/v1/boiler/` to keep boiler endpoints isolated
* Creating new files:
	+ `odin/api/v1/boiler/__init__.py`
	+ `odin/api/v1/boiler/serializers.py` with `BoilerStatusSerializer`
	+ `odin/api/v1/boiler/views.py` with `BoilerStatusView`
	+ `odin/api/v1/boiler/urls.py`
	+ `odin/tests/api/test_boiler.py`
* Modifying existing files:
	…

## Test Results

- Session status: `resolved`
- OpenCode session id: `ses_f4b56ab55ffeECmuDC8xiKVJm9`

---

## Follow-ups

- None

## References

- External: https://linear.app/mnt/issue/MNT-208/boiler-dashboard
