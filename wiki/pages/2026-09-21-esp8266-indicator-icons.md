---
title: 'ESP8266 relay indicators: SVG icons + mode tooltip'
date: '2026-09-21'
type: implementation
status: resolved
session_id: ses_f3beaf3e2ffeUG8I6vlzCO42fI
services: [frontend]
branch: -
tickets: []
tags: [frontend, esp8266, relay, indicators, svg]
related: [2026-09-18-relay-state-mode-refactor, 2026-09-19-mnt-215-midseason-mode]
---
# ESP8266 relay indicators: SVG icons + mode tooltip

## TL;DR

Replaced the blue/red dot alive indicators in the ESP8266 tile with SVG icons for
ON/OFF relay states, red/grey dots for UNKNOWN/IGNORED, and moved the relay `mode`
into a `title` tooltip on the indicator (dropping the one-letter mode block).
All frontend checks (typecheck, Biome lint, production build) and dashboard tests pass.

---

## Overview

The ESP8266 dashboard tile rendered each relay as a colored dot derived from
`relay.is_on` (`cooling`/`heating`) plus a separate one-letter mode block
(`sensor.relay.mode[0]`). At the time the relay model had four `state` values —
ON, OFF, IGNORED, UNKNOWN — so the indicator had to distinguish them, and `mode`
(a multi-letter enum like `SUMMER`, `MIDSEASON`, `BASIC`) is too long for a
one-letter block.

> **Note 2026-09-25 (Consistency Agent):** `RelayState.IGNORED` was removed in
> [[2026-09-19-mnt-215-midseason-mode]]; `RelayState` now has **three** values
> (ON/OFF/UNKNOWN) and `IGNORED` survives only as a `RelayMode`. The current
> `relayIndicator()` (`frontend/src/components/tile/Esp8266SensorsTile.tsx:22`)
> has no `state="IGNORED"` branch and maps `ON → cooling`, `OFF → heating`, the
> inverse of the snippet below.

## Step 1 — Indicator mapping in `Esp8266SensorsTile.tsx`

Added a `relayIndicator()` helper. It checks `relay.mode` first for the indicator
states, then falls back to `relay.state` for the icons — important because a servo
whose related pump is OFF reports `state=OFF` with `mode=IGNORED`, so the grey/red
dot must not be swallowed by the icon branches:

- `mode=IGNORED` → grey dot (`alive-indicator--ignored`)
- `mode=UNKNOWN` → red dot (`alive-indicator--unknown`)
- `state=ON` → `heating` SVG icon
- `state=OFF` → `cooling` SVG icon
- `state=IGNORED` → grey dot
- anything else / null → red dot

Tooltip (`title`) falls back `mode ?? state`. Removed the `sensor-row__mode` block
entirely.

**File:** frontend/src/components/tile/Esp8266SensorsTile.tsx:22

```tsx
function relayIndicator(relay: DashboardRelay): ReactNode {
  const tooltip = relay.mode ?? relay.state ?? undefined;
  switch (relay.mode) {
    case "IGNORED":
      return <AliveIndicator state="ignored" title={tooltip} />;
    case "UNKNOWN":
      return <AliveIndicator state="unknown" title={tooltip} />;
  }
  switch (relay.state) {
    case "ON":
      return <Icon name="heating" alt="heating" width={20} title={tooltip} />;
    case "OFF":
      return <Icon name="cooling" alt="cooling" width={20} title={tooltip} />;
    case "IGNORED":
      return <AliveIndicator state="ignored" title={tooltip} />;
    default:
      return <AliveIndicator state="unknown" title={tooltip} />;
  }
}
```

> **Fix:** the initial version switched only on `relay.state`, so an IGNORED servo
> (reported as `state=OFF` + `mode=IGNORED` by `RelayTargetStateService`) rendered
> the `cooling` icon instead of the grey dot. Mode is now checked first.

## Step 2 — Supporting components and styles

- `AliveIndicator.tsx` — `AliveState` changed from `"alive" | "dead" | "heating" |
  "cooling"` to `"alive" | "dead" | "unknown" | "ignored"`; added optional `title` prop.
- `Icon.tsx` — added optional `title` prop (rendered on the `<img>`).
- `dashboard.ts` — `DashboardRelay.state` / `mode` typed `string | null` (API can
  return null for un-refreshed relays).
- `components.css` — `--unknown` uses `--color-error`, `--ignored` uses
  `--color-text-tertiary`; removed `--cooling` / `--heating` dot rules.
- `tiles.css` — removed unused `.sensor-row__mode`.
- `StyleguidePage.tsx` — `ALIVE_STATES` updated to `alive` / `dead` / `unknown` /
  `ignored`.

**Files:** frontend/src/components/tile/AliveIndicator.tsx:1,
frontend/src/components/icons/Icon.tsx:10, frontend/src/lib/api/dashboard.ts:3,
frontend/src/styles/components.css:82, frontend/src/styles/tiles.css,
frontend/src/pages/StyleguidePage.tsx:14

## Test Results

- `make frontend-typecheck` — pass
- `make frontend-lint` (Biome) — pass
- `bun run --cwd frontend build` — pass
- `pytest odin/tests/views/test_dashboard.py` — 9 passed

---

## Follow-ups

- None

## References

- Related: [[2026-09-18-relay-state-mode-refactor]]