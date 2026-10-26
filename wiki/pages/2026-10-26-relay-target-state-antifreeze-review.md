---
title: 'RelayTargetStateService review — antifreeze fail-safe and rule order'
date: '2026-10-26'
type: code-review
status: resolved
session_id: ses_relay_target_state_antifreeze_review_2026_10_26
services: [relays-services, boiler-mode, weather-models]
branch: master
tickets: []
tags: [relays, antifreeze, fail-safe, force_state, override, midseason, weather, pump, servo, valve, code-review]
related: [2026-10-25-mnt-255-override-by-schedule.md, 2026-10-15-mnt-250-schedule-cycle-rule.md,
  2026-09-19-mnt-215-midseason-mode.md, 2026-10-11-midseason-pump-cadence-30min.md,
  2026-10-22-mnt-253-midseason-humidity-wind-research.md, 2026-09-23-relay-mode-compute-on-read.md,
  2026-09-17-mnt-206-boiler-mode-controller.md]
---

# RelayTargetStateService review — antifreeze fail-safe and rule order

## TL;DR

Reviewed the uncommitted rewrite of `RelayTargetStateService` in `odin/apps/relays/services.py` that adds an
antifreeze fail-safe for missing weather. The draft is not shippable: `get_weather_mode()` returns `None` both for
"no weather" and for the whole `-8 … 10 °C` band, so the fail-safe turns the entire heating season into
`(ON, ANTIFREEZE)` for pumps and `(OFF, UNKNOWN)` for servos, and the move of `force_state` / override into the pump
branch dropped both for servos and valves. Against the working tree the relay and boiler-mode tests give
98 failed / 107 passed. The author then fixed the contract in review; the final rule order and the change list are
recorded below. Tests, `AGENTS.md` and the MNT-255 page are to be re-baselined *after* the service is rewritten.

## Scope

- Reviewed: unstaged diff of `odin/apps/relays/services.py` and every call site of `get_target_state()` —
  `RelaySerializer` / `DashboardRelaySerializer` (mode on read), `RelayRetrieveUpdateView.perform_update`,
  `RelayAdmin.save_model`, `BoilerModeService.get_pumps_state()`.
- Not reviewed on purpose: tests, `AGENTS.md` and the wiki hunks, which the author confirmed are stale and will be
  updated after the code lands.
- Checks run: `ruff check`, `ruff format --check` and `ty check` on the module (clean); pytest over
  `odin/tests/models/test_relays.py`, `odin/tests/api/test_relays.py` and
  `odin/tests/services/test_boiler_mode_controller.py`.

```text
98 failed, 107 passed in 2.58s
```

## What the draft does

Pump order: no band or antifreeze → `ON/ANTIFREEZE`; `force_state`; `SUMMER` → `OFF`; override period; `MIDSEASON`
cadence. The cycle window, the `schedule` periods and `FALLBACK` are unreachable because every band value is
consumed first, so the whole MNT-250 winter behaviour is dead code.

Servo order: no sensor / stale / no reading / no band → `OFF/UNKNOWN`; antifreeze and summer → `OFF`; related pump
off → `IGNORED`; cycle window; sensor regulation. Servos regulate in midseason and never in winter. Neither
`force_state` nor the override is consulted for a servo.

Valve: always `(UNKNOWN, FALLBACK)`. At HEAD valves honoured `force_state` and the override.

## Findings

1. **Docs described an implementation that does not exist.** The unstaged `AGENTS.md` and wiki hunks talk about a
   fail-safe placed first in `get_target_state()` for every relay type, a `TestRelaysAntifreezeFailSafe` class and
   a `pin_weather_band()` helper with 195 relay tests passing. None of that is in the tree, no branch or stash has
   those names. Author confirmed: the docs are stale and will follow the code.
2. **The dead band is swallowed by the fail-safe.** `-8 ≤ temp ≤ 10 °C` was the band where pumps follow the cycle
   and schedule and servos regulate by room temperature (kept deliberately in the MNT-250 review). The draft runs
   the pump continuously and keeps every servo open all winter.
3. **Force state and override dropped for servos and valves.** At HEAD both were checked once in
   `get_target_state()` for all types, including the servo inversion for an `ON` override merged in MNT-255. The
   API still accepts `force_state` and `override_schedule` on servos, so the UI would show a change with no effect.
4. **A pump cannot be forced off in the dead band or below `-8 °C`.** Antifreeze deliberately outranks
   `force_state`; combined with finding 2 that blocks any manual stop during the heating season.
5. **Summer beat the override for pumps**, contradicting MNT-255 where the override beat every weather band.
6. **Servo midseason behaviour silently changed.** MNT-215 and the MNT-250 review decided servos stay
   `(OFF, MIDSEASON)` for the whole band; the draft let them regulate.
7. **Servo fail-safe label was `UNKNOWN`, pump label `ANTIFREEZE`.** The dashboard tile renders `UNKNOWN` as the
   grey fault indicator, so a weather outage would look like a dead sensor on every servo.
8. **Boiler mode flips to permanent `MIXED` in winter.** `BoilerModeService.get_pumps_state()` aggregates the
   computed pump state, which is never `OFF` below `10 °C` in the draft. The periodic controller is disabled in the
   scheduler, so no production impact yet, but two boiler tests fail.
9. **The fail-safe never fires on stale weather.** `Weather.objects.current()` falls back to the last row
   regardless of age (and, having no `Meta.ordering`, to the highest pk, which can be a *future* forecast slot).
   "No weather" only happens with an empty table or a null temperature; a dead pogoda.by feed keeps the last band
   forever.
10. **Larger step at the `10 °C` edge.** Crossing `10.0 → 10.1 °C` jumps a pump from continuous `ON` to the
    midseason daytime cadence.

Minor: `get_context()` was only moved (diff noise); comment typos "meaningfull" and "Forced state always have";
the `get_weather_mode()` docstring still says "None when no band applies", which is the conflation in finding 2;
`get_current_period()` reads `timezone.localtime()` again instead of `self.now` (pre-existing).

## Decisions

Answers from the author during the review:

- Fail-safe is for **missing weather only**; `-8 … 10 °C` follows the default rules when sensor data and at least
  a weather temperature exist (humidity and wind stay optional).
- Antifreeze outranks `force_state = OFF`; summer never outranks any `force_state`.
- Midseason: servos always open, pumps follow the daytime cycle rule.
- The heat direction of a force (pump `ON`, servo `OFF`) always applies; with no data it is the only state
  possible anyway. The stop direction (pump `OFF`, servo `ON`) applies only with data and not in antifreeze.
  "Data" for a servo means weather **and** a live sensor.
- The override schedule sits right after `force_state` and follows the same asymmetry.
- A forced or overridden servo close does **not** beat `IGNORED` (related pump off).
- Servo with no weather and a dead sensor reports `UNKNOWN`.
- When a force coincides with or is outranked by the fail-safe the label is `ANTIFREEZE`.
- Valves: `force_state` and override apply, weather is irrelevant (HEAD behaviour).
- A weather row older than **two hours** counts as "no weather".
- `temp ≥ 10 °C` is midseason; no hysteresis at the edge.
- Servo fail-safe answer mirrors the pump: `(OFF, ANTIFREEZE)`.

## Final rule order

Pump:

1. No usable weather, or `temp < -8` → `(ON, ANTIFREEZE)`. Any force or override is ignored, label stays
   `ANTIFREEZE`.
2. `force_state` → `(force_state, FORCED)`.
3. Override period → `(target_state, OVERRIDE)`.
4. `SUMMER` → `(OFF, SUMMER)`.
5. `MIDSEASON` → daytime cadence `hour >= 6 and is_cycle_window()`, `(ON|OFF, MIDSEASON)`.
6. Default band `-8 ≤ temp < 10` → cycle window `(ON, CYCLE)`, then schedule period `BASIC`, else
   `(ON, FALLBACK)`.

Servo:

1. No sensor, stale sensor or no reading → `(OFF, UNKNOWN)` (also covers no weather + dead sensor).
2. No usable weather, or `temp < -8` → `(OFF, ANTIFREEZE)`.
3. Related pump off → `(OFF, IGNORED)`; beats a forced or overridden close.
4. `force_state` → `(force_state, FORCED)`.
5. Override period → inverted, `(OFF|ON, OVERRIDE)`.
6. `SUMMER` and `MIDSEASON` → `(OFF, band)`.
7. Default band → cycle window `(OFF, CYCLE)`, then sensor regulation `BASIC`, else `(OFF, FALLBACK)`.

Valve: `force_state`, then override, else `(UNKNOWN, FALLBACK)`.

Weather band: a row is usable only when it has a temperature and is at most two hours old. `temp < -8` is
antifreeze, `-8 ≤ temp < 10` is the default band, `temp ≥ 10` is midseason, the existing Steadman gate still
extends midseason up to `20 °C`, otherwise summer.

### Open detail: which timestamp is "two hours old"

`WeatherManager.current()` first looks for the row of the current hour and otherwise returns the highest-pk row,
which can be a forecast slot in the future from the last successful fetch. Two candidates:

- **`period`** — distance between the forecast slot and now; guards against using the wrong hour.
- **`synced_at`** — time since the feed last wrote the row (`auto_now`, refreshed every 30 min by
  `update_weather`); guards against a dead feed.

Recommendation: usable only when the slot is within two hours of now in either direction **and** it was synced
within the last two hours. Both checks are cheap and cover both failure modes.

## Change list for `odin/apps/relays/services.py`

1. Replace the `RelayMode | None` return of `get_weather_mode()` with a private band enum (none, antifreeze,
   default, midseason, summer) and map to `RelayMode` only where a mode is reported. This separates "no weather"
   from the default band without a `RelayMode` migration. (Shipped as `WeatherMode` / `get_weather_mode()` —
   the `WeatherBand` / `get_weather_band()` names in the draft change list were renamed before landing.)
2. Add the freshness check to the band resolution, with the two-hour threshold as a class constant next to the
   temperature constants. Keep `Weather.objects.current()` unchanged for the dashboard tile, or give it a
   `max_age` parameter so the boiler service can reuse it.
3. Change the midseason lower edge from `>` to `>=` on `MIDSEASON_TEMP_MIN`.
4. Extract one helper for "force then override" returning an optional `(state, mode)`, with the servo inversion
   inside, and call it from all three type branches at the positions above. This restores force and override for
   servos and valves and removes the duplicated override block.
5. Rewrite `get_pump_target_state()` in the order above; the cycle, schedule and fallback branches become reachable
   again for the default band.
6. Rewrite `get_servo_target_state()` in the order above, restoring the unconditional `(OFF, MIDSEASON)` and
   placing `IGNORED` before the force helper.
7. Give the valve branch the force helper and keep `(UNKNOWN, FALLBACK)` as its fallback.
8. Fix the `get_weather_mode()` docstring and the two comment typos; drop the pure move of `get_context()`.
9. `BoilerModeService.get_target_mode()` needs no logic change, but switch its own no-weather check to the same
   freshness helper so the boiler and the relays agree on what "no weather" means.

## Resolution

Applied 2026-10-26, in the same session as this review:

- `odin/apps/relays/services.py` — `WeatherMode` enum + rewritten `get_weather_mode()`,
  `get_manual_target_state()` shared by pump/servo/valve, the three type branches reordered as above,
  `get_context()` back in its original position. (The draft change list above called these `WeatherBand` /
  `get_weather_band()`; the landed names are `WeatherMode` / `get_weather_mode()`.)
- `odin/apps/weather/services.py` — `get_latest_weather()` and `WEATHER_MAX_AGE` (two hours, both
  `period` and `synced_at`); `Weather.objects.current()` untouched for the dashboard tile. (The draft
  called the helper `get_fresh_weather()`; the landed name is `get_latest_weather()`.)
- `odin/apps/boiler/services/mode.py` — `get_target_mode()` uses `get_latest_weather()`.
- Tests: `create_weather()` lives in `odin/tests/factories.py`; baseline rows added wherever the
  default band is assumed, dead-band expectations re-baselined to `10.0 → MIDSEASON` /
  `9.9 → CYCLE`; new classes `TestRelaysAntifreezeFailSafe`, `TestRelaysWeatherFreshness` and
  `TestRelaysManualControl`, plus a fail-safe case on the retrieve endpoint and two boiler
  freshness cases. Full `odin/` suite: **539 passed**.
- Docs: the relay bullets in `AGENTS.md` and the fail-safe section of
  [[2026-10-25-mnt-255-override-by-schedule]] now describe this rule order.

## Follow-ups

> **Note 2026-10-26 (Consistency Agent):** the items below were applied later the same session —
> see [Resolution](#resolution) (new fail-safe/freshness/manual-control test classes, `AGENTS.md`
> relay bullets and the `MNT-255` fail-safe section rewritten, full `odin/` suite **539 passed**,
> verified again this pass). Kept here as the original review record.

- Re-baseline `odin/tests/models/test_relays.py`, `odin/tests/api/test_relays.py` and
  `odin/tests/services/test_boiler_mode_controller.py` against the final rule order; add cases for the fail-safe per
  type, the two-hour staleness guard, force/override asymmetry, `IGNORED` beating a forced close and the `10 °C`
  edge.
- Rewrite the relay-control bullets in `AGENTS.md` and the "Antifreeze fail-safe" section of
  [[2026-10-25-mnt-255-override-by-schedule]] to match the code; drop the invented test names and counts.
- Environment: the project `.venv` scripts still point at the old `home/odin/` path, so `uv run pytest` fails to
  spawn; `uv run python -m pytest` works, and `make install` after deleting `.venv` fixes it properly.

## References

- Related: [[2026-10-25-mnt-255-override-by-schedule]] — override rule whose placement is restored here
- Related: [[2026-10-15-mnt-250-schedule-cycle-rule]] — the `-8 … 10 °C` default band and cycle rule kept alive
- Related: [[2026-09-19-mnt-215-midseason-mode]] — servos always open in midseason
- Related: [[2026-10-11-midseason-pump-cadence-30min]] — pump daytime cadence
- Related: [[2026-10-22-mnt-253-midseason-humidity-wind-research]] — raw-temp antifreeze edge, Steadman gate
- Related: [[2026-09-23-relay-mode-compute-on-read]] — why every call site computes mode on read
- Related: [[2026-09-17-mnt-206-boiler-mode-controller]] — `get_pumps_state()` consumer of the pump state
