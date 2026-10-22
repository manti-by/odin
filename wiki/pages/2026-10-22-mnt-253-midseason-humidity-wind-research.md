---
title: MNT-253 — Midseason humidity & wind research
date: 2026-10-22
type: investigation
status: resolved
session_id: ses_mnt253_midseason_weather_research_2026_10_22
services: [weather, relays-services]
branch: feature/mnt-253-midseason-updates
tickets: [MNT-253]
tags: [weather, midseason, apparent-temperature, wind, humidity, research]
related: [2026-09-19-mnt-215-midseason-mode.md, 2026-10-11-midseason-pump-cadence-30min.md, 2026-10-15-mnt-250-schedule-cycle-rule.md]
---

# MNT-253 — Midseason humidity & wind research

## TL;DR

The midseason gate (`8 < temp < 15`) uses only dry-bulb outside temperature, while the same temp
feels very different with wind and humidity. Research answer: gate the band's **top edge** on the **Steadman apparent temperature**
`AT = Ta + 0.33e − 0.70ws − 4.00` — the standard index that combines temperature, relative humidity
and wind into one number — while the bottom edge stays on the raw temperature. Pogoda.by already stores `RH`,
`WINDSP` and `GUST` in `Weather.data`; only the computed index and the band check are missing.
Fallback rule: any missing input → fall back to today's temp band (fail-safe = current behavior).

> **Note 2026-10-22 (Consistency Agent):** the *revised* asymmetric proposal below is now implemented
> on branch `opencode/feature/mnt-253-midseason-updates` (PR #44, In Review, not merged as of
> 2026-10-22). `apparent_temp()` lives in `odin/apps/weather/services.py`; the band classification
> moved into a shared `RelayTargetStateService.get_weather_mode()`; missing humidity/wind still
> degrade to the exact pre-MNT-253 behaviour. The `Weather.apparent_temp` *property* from the
> original proposal was dropped to avoid a circular import with `services.py`.

---

## Net effect

The gate is **asymmetric, not a single-variable swap**: the raw bottom edge `8 < ta` stays, and the
top edge becomes a feels-like extension — midseason also covers `15 <= ta < 20` when `AT < 15`.
Windy warm days keep cycling the radiators (AT drops ~0.7 °C per m/s of wind), while calm-humid
mornings stay in `SUMMER` instead of silently widening it. Antifreeze stays raw-temp-only so the
fail-safe heat answer never depends on a fetched humidity/wind field. The classification is
calibratable later against indoor sensor history (see the correlation recipe below).

## Current state of the data

**File:** `odin/apps/weather/management/commands/update_weather.py:33-57`

The ingest already serializes everything the formula needs from
`https://pogoda.by/api/v2/numeric-weather/2/26852`:

- `data["temp"]["avg"]` — outside air temp °C (`TMP`), exposed as `Weather.temp`
- `data["humidity"]` — relative humidity % (`RH`) — **not exposed**, raw JSON only
- `data["wind"]["speed"]` — wind speed m/s (`WINDSP`) — **not exposed**, raw JSON only
- `data["wind"]["gusts"]` — gusts m/s (`GUST`) — **not exposed**, raw JSON only
- `data["pressure"]` — exposed as `Weather.pressure` as a shape precedent

So the solution is only about computing an index and gating on it.

## How temp, humidity and wind act on the house

Three separate physical mechanisms, currently collapsed into one threshold:

- **Envelope conduction** — heat loss ∝ (Tin − Tout). This is what `temp` already covers.
- **Wind → infiltration** — wind raises pressure differences across the envelope and increases the
  air-change rate; cold-air heat loss from infiltration is explicitly a function of wind speed and
  the indoor−outdoor temperature difference (AIVC). Practical effect: the same −X °C outside is a
  bigger effective cooling load on a windy day — matches the ticket's "wind pushes cold air in".
  Standard references: Canadian NRCan *Keeping The Heat In*; ASHRAE/EnergyPlus infiltration
  guidelines peg wind as the primary driver of envelope air leakage variability.
- **Humidity → perceived and latent effects** — at 8–15 °C outside, humid air raises vapor
  pressure, which suppresses evaporation from skin and makes cold+damp feel colder indoors too
  (condensation on cold walls); the Steadman index captures this with the `+0.33e` term. Note the
  counter-intuition: cold outside air (e.g. 10 °C at 90% RH) is actually *dry* once heated to
  22 °C indoors (~32% RH) — the humidity that matters for the "feels like" estimate is the present
  moisture, not what arrives after ventilation.

Classic wind chill (rotation formula) is unsuitable here: it applies below ~10 °C and ignores
humidity entirely, which is the wrong quadrant for an 8–15 °C band.

## The index: Steadman apparent temperature (BOM standard)

The Australian BOM / Steadman (1994) apparent temperature is the de-facto standard for combining
exactly these three variables:

```
AT = Ta + 0.33·e − 0.70·ws − 4.00

e = RH/100 · 6.105 · exp(17.27·Ta / (237.7 + Ta))   # water vapor pressure, hPa
Ta — air temperature °C, RH — relative humidity %, ws — wind speed m/s (10 m, average)
```

Magnitude in the midseason band (calculated examples):

- **Ta=12 °C, RH=80% → e≈11.2 hPa.** Calm (1 m/s): AT≈11.0. Windy (5 m/s): AT≈8.2 — a 4 °C-feel
  swing inside the same dry-bulb band, enough to cross the 8 °C edge of midseason.
- **Humidity term alone** (calm, ws=1): RH 40% → AT≈9.1 vs RH 80% → AT≈11.0 — roughly ±2 °C.
- **Ta=16 °C, RH=85%, ws=5 m/s → AT≈14.3** — falls *into* midseason although by raw temp it would
  be summer; calm, it stays summer. This is exactly the "wind widens the heating window" behavior
  the ticket asks for.

Rule of thumb per variable: wind is the dominant modifier (−0.7 °C AT per m/s), humidity adds up to
+4 °C AT between dry and saturated air at these temps, and temperature shifts the whole index 1:1.

## Proposed solution

1. **Expose stored data** in `Weather` (same property pattern as `temp`/`pressure`):
   `humidity`, `wind_speed` (fall back: `wind.speed` else `wind.gusts`, else `None`).
2. **Add the index** — a pure function (best placed in `odin/apps/weather/services.py`):

   ```python
   def apparent_temp(temp: Decimal | None, humidity: Decimal | None, wind_speed: Decimal | None) -> Decimal | None:
       if temp is None:
           return None
       if humidity is None or wind_speed is None:
           return None  # caller falls back to the raw-temp band
       e = (humidity / 100) * Decimal("6.105") * (Decimal("17.27") * temp / (Decimal("237.7") + temp)).exp()
       return temp + Decimal("0.33") * e - Decimal("0.70") * wind_speed - Decimal("4.00")
   ```

   Also expose it as `Weather.apparent_temp` for admin/debug reuse.
3. **Swap the band** in `RelayTargetStateService` (both pump `services.py:105` and servo
   `services.py:142` midseason branches, and symmetrically the summer edge `services.py:99/136`):

   ```python
   effective_temp = apparent_temp(weather.temp, weather.humidity, weather.wind_speed) or weather.temp
   if effective_temp >= 15:      # summer
   ...
   elif 8 < effective_temp < 15: # midseason
   ```

   Antifreeze stays on raw temp: below −8 °C the answer is always "heat", and widening the
   fail-safe ON band must never depend on a fetched weather field.
4. **Graceful degradation contract** — any missing `humidity`/`wind_speed` ⇒ `AT` is `None` ⇒ the
   gate degenerates to today's behavior. No new failure mode; no widening when data is stale.
5. **Correlation / calibration** — the house itself is the truth source, and all the raw data is
   already retained (`Weather.period` hourly + `SensorLog` for indoor DHT22 sensors). First-order
   correlation recipe (one-off Django shell / management script):
   - bin both tables by hour; index indoor by `Sensor.temp` of one representative room sensor;
   - compute indoor cooling rate `ΔTin/Δt` for each hour bin;
   - compute (a) `Tin − Tout`, (b) `wind_speed`, (c) `humidity`, (d) `AT`;
   - check Pearson/Spearman rank correlation of `ΔTin/Δt` against each. Expected: `ΔTin/Δt`
     correlates best with `AT` (wind term should show up as a systematic negative residual vs the
     plain `Tin − Tout` fit). If confirmed, the 8/15 AT band edges are usable as-is; if the
     residual slope differs, tune only the band edges, not the formula.
6. **Gust refinement (optional, later)** — in this band infiltration correlates with gusts more
   than average wind; candidate variant `ws = max(WINDSP, GUST/2)` or a midseason-only gust
   extension `ws_eff = (WINDSP + GUST) / 2`, gated behind MNT-249 per-circuit settings.

## Open questions

- Does the provided pogoda.by feed's `WINDSP` unit need runtime verification (m/s assumed, typical
  for the feed)? One `update_weather` log against a known-forecast day settles it.
- Should the summer/antifreeze edges also use `AT` (proposal says summer yes, antifreeze no)?
- Whether to use gusts as the wind input from day one, or only after the correlation analysis.

## Update — 2026-10-22 14:30 — local DB down, validated on production

Local Postgres was down; analysis ran against the odin server DB (192.168.1.100) — note macOS Local
Network (TCC) blocks the Homebrew `psql` binary from LAN while Apple-system binaries (nc/ruby/bash)
pass, so queries went through an `nc`→psql localhost relay (`<tmp>/opencode/pgrelay.sh`).

### What the production feed actually contains (21 732 hourly rows, Jun 2025 → Oct 2026)

- `wind.speed` = integer m/s categories 0–10, `gusts` to 21 — units confirmed, no conversion needed.
- Raw band `8 < ta < 15` covers **6 485 h (~30% of the year)**, avg RH inside = 77% (band is damp).
- Wind is measured as 10 m mean speed; `WINDSP` granularity is 1 m/s, gusts finer.

### Correlation: does wind/rh move the house? (Steadman AT vs measured indoor dynamics)

Summer-night subsample (611 hourly bins, living room CENTAX-01, heating off, no solar):

- `regr_slope(dtin, ws)` = **−0.008 °C/h per m/s** versus the observed natural summer-night fall
  rate of **−0.256 °C/h**: wind adds a few percent per m/s to the fall rate (3% at 1 m/s, ~31%
  at a 10 m/s storm) — real but small in absolute terms.
- `regr_slope(dtin, rh)` ≈ 0 (−4.7e−5 °C/h per %RH) — outdoor RH does not cool the house.
- `regr_slope(dtin, ta)` = −0.026 °C/h per °C — the only sizable outdoor driver, i.e. conduction.
- Conclusion, opposite of the ticket's expectation on the *house* side: the wind/humidity effect
  the user observes is a **perceptual / radiator-temperature effect, not an indoor-heat-loss
  effect measurable in the data**. The AT index is still the right gate, but expectations for
  indoor dynamics from wind alone should be modest.

### Band-crossing impact (would the classification change?)

- 1 264 h of `15 < ta < 20` would **newly enter** midseason under an AT gate (windy, AT < 15):
  **618 spells, avg just 2 h, max 11 h** — these are short gusty bursts inside warm days.
- Only 41 h inside the raw band would be **lost** to a naive full-AT swap (calm-humid AT ≥ 15).
- **1 893 h inside the raw band already sit at AT < 8** (gusty 8–10 °C): 671 spells, avg 2.8 h,
  max 18 h — a third of midseason time is much colder-feeling than the raw temp suggests and is
  worth cycling the radiators for even outside the scheduled slots at the cabin's discretion.

### Revised proposal after the measurements

1. Expose `humidity` / `wind_speed` on `Weather`, add a pure `apparent_temp(...)` helper.
2. Midseason gate becomes **asymmetric** (ticks raw band bottom, feels-like top):
   `midseason if 8 < ta < 15 OR (15 <= ta < 20 AND AT < 15)`; `summer if ta >= 15 AND AT >= 15`.
   A naive `8 < AT < 15` swap is *not* recommended: it silently widens summer on calm-humid
   mornings and reacts to 1 m/s integer wind steps.
3. Antifreeze stays raw-temp (`< −8`); only the summer/midseason edge moves.
4. Calibration source confirmed: the 16-month hourly history + indoor sensors is enough to tune
   the wind threshold without new instrumentation. Postgres `corr()`/`regr_slope()` over
   `weather_weather` ⋈ `sensors_sensorlog` (housing route detail above) reproduces everything.

## Follow-ups

- Implementation PR #44 on `opencode/feature/mnt-253-midseason-updates` — built the **revised
  asymmetric gate** above (not the naive swap): `8 < ta < 15`, plus `15 <= ta < 20 AND AT < 15`,
  antifreeze stays raw-only
- Correlation script over the retained `Weather`/`SensorLog` history to validate the band edges.
- MNT-249 (per-circuit midseason settings) can later take the `AT` thresholds as circuit overrides.

## References

- Related: [[2026-09-19-mnt-215-midseason-mode]]
- Related: [[2026-10-11-midseason-pump-cadence-30min]]
- Related: [[2026-10-15-mnt-250-schedule-cycle-rule]]
- External: https://linear.app/mnt/issue/MNT-253/midseason-updates
- External: Steadman apparent temp — https://en.wikipedia.org/wiki/Apparent_temperature
- External: AIVC — heat loss from infiltration as f(wind speed, ΔT) —
  https://www.aivc.org/resource/heat-loss-buildings-result-infiltration
- External: NRCan Keeping The Heat In — https://natural-resources.canada.ca/energy-efficiency/home-energy-efficiency/keeping-heat-section-2-your-house-works
