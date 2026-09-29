---
title: Boiler tile shows no temperatures — API returns override, not live status
date: 2026-09-27
type: debug
status: resolved
session_id: ses_boiler_live_status_api_2026_09_27
services: [boiler, main]
branch: master
tickets: []
tags: [boiler, ebusd, api, react, dashboard]
related: [2026-09-18-mnt-208-boiler-dashboard.md]
---

# Boiler tile shows no temperatures — API returns override, not live status

## TL;DR

The dashboard Boiler tile displayed `—` for Flow/Hot water whenever no override was active. The API
`GET /api/v1/boiler/status/` derived `target_temp`/`hwc_temp` from the saved override file (both
`None` in panel mode), while the `boiler_status` management command reads **live** fields straight
from ebusd via `BoilerStatusService.status()`. Fix: the API now also returns a `status` dict with
the same live fields as the command, and the tile renders live Flow/Return/Tank temps plus setpoints
and modulation. No boiler status/mode/temp logic was touched.

---

## Symptom

"FE boiler component doesn't show temperatures; it should display the same info as `boiler_status`."

The `BoilerTile` showed the mode and schedule rows, but the temperature block rendered `—`:

```
Flow       —
Hot water  —
```

`boiler_status` on the same machine showed real values:

```
FlowTempDesired:      45  (heating flow setpoint, °C)
HwcTempDesired:       55  (hot-water setpoint, °C)
FlowTemp:             48  (actual flow, °C)
ReturnTemp:           37  (actual return, °C)
StorageTemp:          54  (actual tank, °C)
ModulationDesired:    42  (burner modulation, %)
...
```

## Step 1 — Tile reads override-derived values, not live reads

**File:** `frontend/src/components/tile/BoilerTile.tsx` (before) rendered only `status.target_temp`
and `status.hwc_temp`, labelled "Flow" and "Hot water". Those come from the API, not the bus.

**File:** `odin/api/v1/boiler/views.py:14-31` — the API only re-surfaced the saved override:

```
override = service.current_override()
flow_temp = hwc_temp = None
if override:
    _, flow_temp, hwc_temp = parse_override(override)
...
"target_temp": flow_temp,
"hwc_temp": hwc_temp,
```

So in panel mode (`override is None`) both were `None` → tile showed `—`. Even in override mode these
are the *commanded* setpoints, not the boiler's actual state.

## Step 2 — `boiler_status` reads live fields via `service.status()`

**File:** `odin/apps/boiler/management/commands/boiler_status.py:15-17` iterates
`BoilerStatusService.STATUS_FIELDS` and prints `service.status()`, which does a fresh `read -f` per
field:

**File:** `odin/apps/boiler/services/status.py:150-157`

```
for name, _note in self.STATUS_FIELDS:
    try:
        result[name] = self.read_field(name)
    except EbusdError as e:
        result[name] = f"error: {e}"
```

`STATUS_FIELDS` (`status.py:73-83`) covers `FlowTempDesired`, `HwcTempDesired`,
`StorageTempDesired`, `FlowTemp`, `ReturnTemp`, `StorageTemp`, `ModulationDesired`, `Status01`,
`Status02`. The API simply never exposed these.

## Root cause

The boiler status API duplicated only the override state (mode, setpoints, timestamps) and dropped
the live status data that `boiler_status` reads from ebusd. The tile therefore had no source for
real temperatures, so it fell back to the override values — which are legitimately absent in panel
mode. Constraint respected: no changes to boiler status/mode/temp logic, only the API contract and
the tile.

## Resolution / Fix

1. **API** — return the live status alongside the existing override fields.
   **File:** `odin/api/v1/boiler/views.py` added `"status": service.status()`; the serializer
   (`odin/api/v1/boiler/serializers.py`) gained
   `status = serializers.DictField(child=serializers.CharField())`.
2. **FE type** — `frontend/src/lib/api/boiler.ts` added a `BoilerLiveStatus` interface mirroring
   `STATUS_FIELDS` (all `string`, since ebusd returns raw values or `error: ...`).
3. **Tile** — `BoilerTile.tsx` now shows live `FlowTemp`/`ReturnTemp`/`StorageTemp` in the temps
   block (parsed via a new `parseTemp` helper that treats non-numeric/`-`/error strings as "no
   data"), and added rows for the three setpoints and `ModulationDesired`. Updated/Next boil/Clear
   rows and the mode/override badge are unchanged. `target_temp`/`hwc_temp` stay in the API for
   backward compat.
4. **Test** — `odin/tests/api/test_boiler.py` added `test_status__live_fields` asserting the
   response `status` keys equal `STATUS_FIELDS`.

## Test Results

- `uv run pytest --create-db --disable-warnings --ds=odin.settings.test odin/tests/api/test_boiler.py` — 8 passed (incl. new live-fields test)
- `uv run ruff check odin/api/v1/boiler odin/tests/api/test_boiler.py` — clean
- `bun run lint` (Biome) + `bun run typecheck` (tsc) in `frontend/` — clean

## Known follow-up (not fixed this session)

- `status` values are raw strings; when ebusd is down they read `error: ...`. The tile renders them
  as `—` via `parseTemp`, but `ModulationDesired`/`Status01`/`Status02` are shown raw and will show
  the error text. Consider mapping errors to `—` uniformly if ebusd outages are common.
- The live `read -f` per field adds up to 9 ebusd round-trips per poll (60 s). Fine now, but a batch
  read would be cheaper if the tile ever drops to a shorter poll interval.

---

## Follow-ups

- None — this was a self-contained API + FE contract fix.

## References

- Related: [[2026-09-18-mnt-208-boiler-dashboard]]
- Files: `odin/api/v1/boiler/views.py`, `odin/api/v1/boiler/serializers.py`,
  `odin/apps/boiler/services/status.py`, `odin/apps/boiler/management/commands/boiler_status.py`,
  `frontend/src/lib/api/boiler.ts`, `frontend/src/components/tile/BoilerTile.tsx`,
  `odin/tests/api/test_boiler.py`