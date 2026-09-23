---
title: 'MNT-218: Split dashboard API'
date: '2026-09-23'
type: implementation
status: resolved
session_id: ses_f324459a3fferXCgTDgZMsnUOO
services: [CurrencyTile, Ds18b20SensorsTile, Esp8266SensorsTile, SystemErrorsTile,
  TargetTempModal, WeatherTile, useErrorLogs, useExchangeRates, usePollingData, useSensorsDashboard,
  useSystemdStatus, useTraffic, useVoltage, useWeather, core, currency, dashboard,
  electricity, logs, provider, sensors-dashboard, weather, DashboardPage, serializers,
  urls, views, __init__, services, test_currency, test_logs, test_sensors_dashboard,
  test_systemd, test_traffic, test_voltage, test_weather_current, test_context, test_dashboard,
  test_index, pyproject, uv, .sessions, INDEX, 2026-09-23-mnt-218-split-dashboard-api]
branch: mnt-218-split-dashboard-api
tickets: [MNT-218]
tags: [wiki, feature, incomplete, backend]
related: [2026-09-18-mnt-208-boiler-dashboard]
---
# MNT-218: Split dashboard API

## TL;DR

The dashboard API was split into smaller APIs for each frontend component, grouped by Django model. New endpoints, views, and serializers were created, and the frontend was updated to use the new APIs and hooks. The changes resulted in a more modular and maintainable architecture.

---

## Overview

The implementation involved adding new backend views, serializers, and routes under `odin/api/v1/` for each model cluster, and updating the frontend to use the new APIs and hooks in `frontend/src/lib/api/` and `frontend/src/hooks/`. The changes affected various files, including `odin/api/v1/core/views.py`, `odin/api/v1/core/serializers.py`, `frontend/src/pages/DashboardPage.tsx`, and `frontend/src/components/tile/*.tsx`.

## Changed files

- `frontend/src/components/tile/CurrencyTile.tsx` (13/3)
- `frontend/src/components/tile/Ds18b20SensorsTile.tsx` (45/33)
- `frontend/src/components/tile/Esp8266SensorsTile.tsx` (53/41)
- `frontend/src/components/tile/SystemErrorsTile.tsx` (10/2)
- `frontend/src/components/tile/TargetTempModal.tsx` (1/1)
- `frontend/src/components/tile/WeatherTile.tsx` (13/3)
- `frontend/src/hooks/useErrorLogs.ts` (6/0)
- `frontend/src/hooks/useExchangeRates.ts` (6/0)
- `frontend/src/hooks/{useDashboardData.ts => usePollingData.ts}` (17/6)
- `frontend/src/hooks/useSensorsDashboard.ts` (10/0)
- `frontend/src/hooks/useSystemdStatus.ts` (6/0)
- `frontend/src/hooks/useTraffic.ts` (6/0)
- `frontend/src/hooks/useVoltage.ts` (6/0)
- `frontend/src/hooks/useWeather.ts` (6/0)
- `frontend/src/lib/api/core.ts` (7/0)
- `frontend/src/lib/api/currency.ts` (18/0)
- `frontend/src/lib/api/dashboard.ts` (0/104)
- `frontend/src/lib/api/electricity.ts` (10/0)
- `frontend/src/lib/api/logs.ts` (13/0)
- `frontend/src/lib/api/provider.ts` (11/0)
- `frontend/src/lib/api/sensors-dashboard.ts` (41/0)
- `frontend/src/lib/api/weather.ts` (31/0)
- `frontend/src/pages/DashboardPage.tsx` (45/38)
- `odin/api/v1/core/serializers.py` (0/150)
- `odin/api/v1/core/urls.py` (7/4)
- `odin/api/v1/core/views.py` (10/22)
- `odin/api/v1/currency/__init__.py` (0/0)
- `odin/api/v1/currency/serializers.py` (14/0)
- `odin/api/v1/currency/urls.py` (11/0)
- `odin/api/v1/currency/views.py` (20/0)
- `odin/api/v1/electricity/__init__.py` (0/0)
- `odin/api/v1/electricity/serializers.py` (6/0)
- `odin/api/v1/electricity/urls.py` (11/0)
- `odin/api/v1/electricity/views.py` (18/0)
- `odin/api/v1/logs/__init__.py` (0/0)
- `odin/api/v1/logs/serializers.py` (19/0)
- `odin/api/v1/logs/urls.py` (12/0)
- `odin/api/v1/logs/views.py` (25/0)
- `odin/api/v1/provider/__init__.py` (0/0)
- `odin/api/v1/provider/serializers.py` (7/0)
- `odin/api/v1/provider/urls.py` (11/0)
- `odin/api/v1/provider/views.py` (18/0)
- `odin/api/v1/sensors/serializers.py` (51/0)
- `odin/api/v1/sensors/urls.py` (4/0)
- `odin/api/v1/sensors/views.py` (31/1)
- `odin/api/v1/urls.py` (5/0)
- `odin/api/v1/weather/__init__.py` (0/0)
- `odin/api/v1/weather/serializers.py` (42/0)
- `odin/api/v1/weather/urls.py` (11/0)
- `odin/api/v1/weather/views.py` (18/0)
- `odin/apps/core/services.py` (0/56)
- `odin/tests/api/test_currency.py` (43/0)
- `odin/tests/api/test_logs.py` (75/1)
- `odin/tests/api/test_sensors_dashboard.py` (129/0)
- `odin/tests/api/test_systemd.py` (28/0)
- `odin/tests/api/test_traffic.py` (34/0)
- `odin/tests/api/test_voltage.py` (34/0)
- `odin/tests/api/test_weather_current.py` (50/0)
- `odin/tests/services/test_context.py` (0/75)
- `odin/tests/views/test_dashboard.py` (0/230)
- `odin/tests/views/test_index.py` (0/54)
- `pyproject.toml` (1/1)
- `uv.lock` (1/1)
- `wiki/.sessions.json` (2/1)
- `wiki/INDEX.md` (2/0)
- `wiki/pages/2026-09-23-mnt-218-split-dashboard-api.md` (111/0)

## Stat

```text
frontend/src/components/tile/CurrencyTile.tsx      |  16 +-

 .../src/components/tile/Ds18b20SensorsTile.tsx     |  78 ++++---

 .../src/components/tile/Esp8266SensorsTile.tsx     |  94 +++++----

 frontend/src/components/tile/SystemErrorsTile.tsx  |  12 +-

 frontend/src/components/tile/TargetTempModal.tsx   |   2 +-

 frontend/src/components/tile/WeatherTile.tsx       |  16 +-

 frontend/src/hooks/useErrorLogs.ts                 |   6 +

 frontend/src/hooks/useExchangeRates.ts             |   6 +

 .../{useDashboardData.ts => usePollingData.ts}     |  23 ++-

 frontend/src/hooks/useSensorsDashboard.ts          |  10 +

 frontend/src/hooks/useSystemdStatus.ts             |   6 +

 frontend/src/hooks/useTraffic.ts                   |   6 +

 frontend/src/hooks/useVoltage.ts                   |   6 +

 frontend/src/hooks/useWeather.ts                   |   6 +

 frontend/src/lib/api/core.ts                       |   7 +

 frontend/src/lib/api/currency.ts                   |  18 ++

 frontend/src/lib/api/dashboard.ts                  | 104 ----------

 frontend/src/lib/api/electricity.ts                |  10 +

 frontend/src/lib/api/logs.ts                       |  13 ++

 frontend/src/lib/api/provider.ts                   |  11 +

 frontend/src/lib/api/sensors-dashboard.ts          |  41 ++++

 frontend/src/lib/api/weather.ts                    |  31 +++

 frontend/src/pages/DashboardPage.tsx               |  83 ++++----

 odin/api/v1/core/serializers.py                    | 150 --------------

 odin/api/v1/core/urls.py                           |  11 +-

 odin/api/v1/core/views.py                          |  32 +--

 odin/api/v1/currency/__init__.py                   |   0

 odin/api/v1/currency/serializers.py                |  14 ++

 odin/api/v1/currency/urls.py                       |  11 +

 odin/api/v1/currency/views.py                      |  20 ++

 odin/api/v1/electricity/__init__.py                |   0

 odin/api/v1/electricity/serializers.py             |   6 +

 odin/api/v1/electricity/urls.py                    |  11 +

 odin/api/v1/electricity/views.py                   |  18 ++

 odin/api/v1/logs/__init__.py                       |   0

 odin/api/v1/logs/serializers.py                    |  19 ++

 odin/api/v1/logs/urls.py                           |  12 ++

 odin/api/v1/logs/views.py                          |  25 +++

 odin/api/v1/provider/__init__.py                   |   0

 odin/api/v1/provider/serializers.py                |   7 +

 odin/api/v1/provider/urls.py                       |  11 +

 odin/api/v1/provider/views.py                      |  18 ++

 odin/api/v1/sensors/serializers.py                 |  51 +++++

 odin/api/v1/sensors/urls.py                        |   4 +

 odin/api/v1/sensors/views.py                       |  32 ++-

 odin/api/v1/urls.py                                |   5 +

 odin/api/v1/weather/__init__.py                    |   0

 odin/api/v1/weather/serializers.py                 |  42 ++++

 odin/api/v1/weather/urls.py                        |  11 +

 odin/api/v1/weather/views.py                       |  18 ++

 odin/apps/core/services.py                         |  56 -----

 odin/tests/api/test_currency.py                    |  43 ++++

 odin/tests/api/test_logs.py                        |  76 ++++++-

 odin/tests/api/test_sensors_dashboard.py           | 129 ++++++++++++

 odin/tests/api/test_systemd.py                     |  28 +++

 odin/tests/api/test_traffic.py                     |  34 +++

 odin/tests/api/test_voltage.py                     |  34 +++

 odin/tests/api/test_weather_current.py             |  50 +++++

 odin/tests/services/test_context.py                |  75 -------

 odin/tests/views/test_dashboard.py                 | 230 ---------------------

 odin/tests/views/test_index.py                     |  54 -----

 pyproject.toml                                     |   2 +-

 uv.lock                                            |   2 +-

 wiki/.sessions.json                                |   3 +-

 wiki/INDEX.md                                      |   2 +

 .../2026-09-23-mnt-218-split-dashboard-api.md      | 111 ++++++++++

 66 files changed, 1235 insertions(+), 827 deletions(-)
```

## Build plan

## Implementation Plan
The plan involves splitting the existing dashboard API into smaller APIs for each frontend component, grouped by the used Django model.

### Key Technical Decisions
- New endpoints will be created for each tile/model cluster.
- The old `core/dashboard/` endpoint and related views, serializers, and services will be removed.
- The frontend will be updated to use the new APIs and hooks.

### Backend Changes
- New Django app API packages will be added under `odin/api/v1/` for each model cluster (e.g., `weather/`, `sensors/`, `electricity/`, `provider/`, `currency/`, `logs/`).
- New views and serializers will be created for each endpoint (e.g., `WeatherCurrentView`, `Esp8266DashboardView`, `VoltageCurrentView`).
- The old `DashboardView` and related serializers will be re…

## Test Results

- Session status: `resolved`
- OpenCode session id: `ses_f324459a3fferXCgTDgZMsnUOO`

---

## Follow-ups

- None

## References

- External: https://linear.app/mnt/issue/MNT-218/split-dashboard-api
