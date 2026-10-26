---
title: 'MNT-255: Override by schedule'
date: '2026-10-25'
type: implementation
status: resolved
session_id: ses_mnt_255_override_by_schedule_2026_10_25
services: [relays, models, services, serializers, test_relays, AGENTS,
  0012_alter_relay_mode_alter_relaylog_new_mode_and_more, pyproject, uv]
branch: mnt-255-override-by-schedule
tickets: [MNT-255, MNT-259]
tags: [relays, override, schedule, mode, migration, tests, backend, feature]
related: [2026-09-22-mnt-217-relay-schedule-component.md, 2026-09-23-relay-mode-compute-on-read.md,
  2026-10-15-mnt-250-schedule-cycle-rule.md, 2026-10-22-mnt-253-midseason-humidity-wind-research.md,
  2026-10-26-relay-target-state-antifreeze-review.md]
---

# MNT-255: Override by schedule

> **Merged 2026-10-26 (Dedup Agent):** this page absorbed the companion "MNT-259: Override by
> schedule" record (deleted; session `ses_e8b7535bfffe7ecj0krwIzk25C`, branch
> `mnt-259-override-by-schedule`). Both pages were written on the same day from the same plan; this
> one is the complete record, so it survives and keeps the MNT-255 title, date, session and branch.
> Tickets now list both issues.

## TL;DR

Relays could only be overridden to a hardcoded `force_state`. A new `context["override_schedule"]`
holds time periods with a required `ON`/`OFF` target and, when the current time falls inside one,
it is applied immediately after `force_state` — before the weather bands, the schedule cycle and
the regular `schedule`. The rule reports a new `RelayMode.OVERRIDE` (migration 0012) and works for
pumps, servos and valves. The two relay test modules pass (184 at first merge, 195 on the current
tree); the full `odin/` suite is green on PostgreSQL (521 passed).

> **2026-10-26 update:** the rule order changed — `ANTIFREEZE` now answers *first*, but only for
> missing/unusable weather or `outside_temp < -8`, and the `-8…10 °C` default band follows the
> schedule rules again. See [Antifreeze fail-safe](#antifreeze-fail-safe) and
> [[2026-10-26-relay-target-state-antifreeze-review]].

## Overview

`force_state` is a single persisted ON/OFF column, so "heat 6:00–8:00" had to be re-entered by hand
every day. The `schedule` context key from MNT-217 is already a list of `start_time`/`end_time`
periods with `target_state`/`target_temp`, but it sits at the *bottom* of the priority chain: a
`SUMMER`/`ANTIFREEZE`/`MIDSEASON` weather band or the MNT-250 cycle window always wins, and valves
are rejected outright. The override is the same period shape promoted to the top of that chain.

Decision order in `RelayTargetStateService.get_target_state()`, band by band:

0. no usable weather, or `outside_temp < -8` → `(ON, ANTIFREEZE)`, `(OFF, ANTIFREEZE)` for a servo
1. `force_state` → `(force_state, FORCED)`, inverted for a servo
2. **`override_schedule` → `(target_state, OVERRIDE)`** ← new, inverted for a servo
3. `SUMMER` → `OFF`; `MIDSEASON` → pump cadence / servo open; servo `UNKNOWN`/`IGNORED` before the
   manual helper
4. schedule cycle window → `CYCLE`
5. regular `schedule` period → `BASIC`, else `FALLBACK`

Steps 4 and 5 live in the `-8…10 °C` default band (`WeatherMode.DEFAULT`), which step 0 does *not*
consume: only missing weather and real antifreeze short-circuit. Valves skip the weather entirely —
`force_state`, then the override, else `(UNKNOWN, FALLBACK)`.

## Step 1 — New mode and migration

**File:** `odin/apps/relays/models.py:44`

```python
FORCED = "FORCED", _("Forced")
OVERRIDE = "OVERRIDE", _("Override")
IGNORED = "IGNORED", _("Ignored")
```

`RelayMode` is stored in `Relay.mode` and in `RelayLog.old_mode`/`new_mode`, so
`uv run manage.py makemigrations relays` produced
`0012_alter_relay_mode_alter_relaylog_new_mode_and_more.py` — three `AlterField` operations, no
data migration. `RelayState` also gained `active_values()` next to `active_choices()`, the tuple
used to skip garbage `target_state` values.

## Step 2 — Service rule

**File:** `odin/apps/relays/services.py:81`

The period-matching loop was extracted verbatim from `get_current_period_from_schedule()` so both
schedules share it:

```python
def get_current_period(self, schedule: dict) -> dict | None:
    if not (periods := schedule.get("periods", [])):
        return None
    ...


def get_current_period_from_schedule(self) -> dict | None:
    return self.get_current_period(self.relay.context.get("schedule", {}))


def get_current_override_period(self) -> dict | None:
    return self.get_current_period(self.relay.context.get("override_schedule", {}))
```

The rule used to sit before the `RelayType` dispatch, which is what made valves work. Since
2026-10-26 it lives in `get_manual_target_state()` and every type branch calls it in the same place,
so a servo gets the inversion and a valve still honours the override:

```python
def get_manual_target_state(self, invert: bool = False) -> tuple[RelayState, RelayMode] | None:
    if (force_state := self.relay.force_state) in RelayState.active_values():
        state = RelayState(force_state)
        return self.invert_state(state) if invert else state, RelayMode.FORCED

    if period := self.get_current_override_period():
        if (override_state := period.get("target_state")) in RelayState.active_values():
            state = RelayState(override_state)
            return self.invert_state(state) if invert else state, RelayMode.OVERRIDE

    return None
```

At HEAD the same block sat in `get_target_state()` before the dispatch:

```python
def get_target_state(self) -> tuple[RelayState, RelayMode]:
    if self.relay.force_state is not None:
        return self.relay.force_state, RelayMode.FORCED

    # Override schedule wins over every computed rule, including weather and the schedule cycle
    if period := self.get_current_override_period():
        if (override_state := period.get("target_state")) in RelayState.active_values():
            state = RelayState(override_state)
            # A servo's ON closes the circuit, so an ON override (heat/run) must open it
            if self.relay.type == RelayType.SERVO:
                state = RelayState.OFF if state == RelayState.ON else RelayState.ON
            return state, RelayMode.OVERRIDE

    match self.relay.type:
        ...
```

`end_time` stays exclusive and overnight spans (`22:00–06:00`) are supported because that logic was
not touched — only the period source moved. A period whose `target_state` is missing, `None` or not
`ON`/`OFF` is skipped, so the normal rules still answer instead of the relay freezing.

`get_current_period()` also tolerates hand-edited context: it returns `None` unless the schedule is a
dict holding a list of period dicts, and skips entries whose `start_time`/`end_time` cannot be parsed
(`KeyError`, `TypeError` from `None`/non-string values, `ValueError`). Before this guard a
`{"start_time": null}` in the admin JSON field raised out of every relay read, turning the list and
retrieve endpoints into 500s. This applies to both `schedule` and `override_schedule`.

`target_state` is **logical** — `ON` means "heat/run" — because pump and servo states are inverted
in this domain: a pump `ON` starts the pump, while a servo `ON` closes the circuit (disables the
loop). Without the inversion an `ON` override window would heat through the pump and close the
servo valve of the same circuit, i.e. the opposite of the intent. Valves carry no inversion.

## Step 3 — Serializers

**File:** `odin/api/v1/relays/serializers.py:55`

The zero-duration and overlap checks moved out of `RelayScheduleSerializer.validate_periods` into a
module-level `_validate_schedule_periods()`, now shared by both schedules. The override pair mirrors
the regular one but drops `target_temp` and makes `target_state` required:

```python
class RelayOverridePeriodSerializer(BaseSerializer):
    start_time = serializers.RegexField(TIME_PATTERN, error_messages={"invalid": TIME_ERROR})
    end_time = serializers.RegexField(TIME_PATTERN, error_messages={"invalid": TIME_ERROR})
    target_state = serializers.ChoiceField(choices=("ON", "OFF"))


class RelayOverrideScheduleSerializer(BaseSerializer):
    periods = serializers.ListField(
        child=RelayOverridePeriodSerializer(), max_length=MAX_SCHEDULE_PERIODS, required=False
    )
```

Both live under `RelayUpdateContextSerializer`, so `context["override_schedule"]` is merged next to
`schedule` by `perform_update` and the recomputed `(state, mode)` is published to Redis — the view
needed no change.

A PATCH is a partial update, and DRF skips `required` nested fields when the root serializer is
partial, so `RelayUpdateSerializer.validate()` re-checks every override period explicitly and raises
`"Override schedule periods require target_state"`. The shared `_validate_schedule_periods()` also
reads the times with `.get()` and raises `"Schedule period requires start_time and end_time"` when
either is missing — subscripting there would surface as an HTTP 500 on a partial PATCH. The
type-specific schedule rules (servo needs `target_temp`, pump needs `target_state`, valve rejected)
deliberately do not apply: an override is always a state, so any relay type can take one.
`target_temp` in an override period is silently dropped by DRF, matching the state-only contract.

Context example:

```json
{
  "context": {
    "override_schedule": {
      "periods": [{"start_time": "06:00", "end_time": "08:00", "target_state": "ON"}]
    }
  }
}
```

## Step 4 — Baseline test re-baseline

The branch already carried commit `0356c8f`, which moved the weather band to
`10 < outside_temp < 17` (extended to `< 20` by the apparent temperature, edge `< 17`) without
touching the tests. Every midseason test still fed `10.0`, which is no longer `> 10`, so the suite
was red before the feature work started:

- `TestRelaysWeatherModes` and the midseason-at-night cycle test now use `12.0`.
- `TestRelaysApparentTempGate` moved from `16` to `18` (`18 °C`, 85 % humidity, 5 m/s → 16.3 °C
  feels-like → `MIDSEASON`; 1 m/s → 19.1 °C → `SUMMER`); the raw lower edge test uses `9.9`
  (feels-like 3.0 °C) and still expects `CYCLE`, while `10.0` moved to `MIDSEASON` on 2026-10-26.
- `test_relays__cycle_does_not_leak_into_other_temperature_bands` params became
  `18.0/SUMMER`, `10.0/MIDSEASON`, `9.9/CYCLE` (antifreeze edges unchanged).

## Step 5 — Tests

`TestRelaysOverrideSchedule` in `odin/tests/models/test_relays.py` covers: ON and OFF periods,
exclusive `end_time`, overnight spans, `force_state` still winning, the override beating `SUMMER`
weather, the cycle window and a regular schedule period, the schedule applying again outside the
override window, the servo physical outcome (an `ON` heating window yields `OFF`, an `OFF` window
yields `ON`), valve relays, invalid `target_state` being skipped, malformed/unusable context data
being skipped, and a two-period schedule picking the matching one.

`TestRelaysUpdateAPI` gained `_override(*periods)` plus PATCH tests for persistence, recompute and
Redis publish with the clock patched inside the period (`(ON, OVERRIDE)`), missing `target_state`,
missing or malformed time, overlapping periods, more than `MAX_SCHEDULE_PERIODS` periods, `target_temp`
being dropped, and a VALVE relay being accepted. Its `setup_method` clears the cache: the
`relays_update` throttle is 30/min keyed by client address, so the class's PATCH calls would
otherwise accumulate across the suite. `TestRelaysAPI` also asserts the list endpoint survives a
malformed override context instead of returning 500.

## Antifreeze fail-safe

`RelayTargetStateService` answers `ANTIFREEZE` first for two cases only — a missing or unusable
weather row, and `outside_temp < -8` — with pump `(ON, ANTIFREEZE)` and servo `(OFF, ANTIFREEZE)`.
The check runs before `force_state` and the override, so a manual stop cannot stick while the
weather is missing or freezing: that is the whole point of the fail-safe.

"The `-8…10 °C` gap has no band" was the original confusion. `get_weather_mode()` now returns the
private `WeatherMode` enum (`NONE`/`ANTIFREEZE`/`DEFAULT`/`MIDSEASON`/`SUMMER`), so the default band
is a band like any other and keeps the cycle, the regular `schedule` and servo regulation reachable.
Only `WeatherMode.NONE` triggers the fail-safe.

A row is usable only through `get_latest_weather()`: it needs a temperature, a `period` within two
hours of now in either direction, and a `synced_at` within the last two hours. `Weather.objects.current()`
alone is not enough — it is ageless and can even return a future forecast slot.

Consequences worth knowing before touching this code:

- `force_state` and the override reach every type again through one `get_manual_target_state()`
  helper. Servos invert the logical state; a forced or overridden close still loses to `IGNORED`
  (related pump off) and to the fail-safe.
- Boiler mode follows the computed pump state. With no fresh weather every active pump reports `ON`,
  so `BoilerModeService` sees `MIXED`; a pump that is forced `OFF` inside the default band now
  aggregates to `OFF` again.

`TestRelaysAntifreezeFailSafe` covers the pump/servo/valve answers without weather, `temp < -8`,
the fail-safe beating `force_state` and the override, and a servo with a dead sensor reporting
`UNKNOWN`. `TestRelaysWeatherFreshness` pins the two-hour window (old `period`, dead `synced_at`,
future forecast slot, and a row just inside it). `TestRelaysManualControl` covers the servo
inversion, `IGNORED` beating a forced close and valve force handling. Everything else that relies
on the default band creates a fresh `0.0 °C` row through `create_weather()` in
`odin/tests/factories.py`.

## Test Results

- `odin/tests/models/test_relays.py` + `odin/tests/api/test_relays.py` → **184 passed** at first
  merge. After the 2026-10-26 rewrite the relay model module alone is 163 passed, with the fail-safe,
  freshness and manual-control classes added.

  > **Note 2026-10-26 (Consistency Agent):** verified on the current tree — both relay test modules
  > together give **210 passed**, and the full `odin/` suite gives **539 passed** on PostgreSQL.
  > The 163/195/521 figures above are mid-session counts from the rewrite day, kept as record.
- Full `odin/` suite on the rewritten tree (PostgreSQL available) → **539 passed, 0 failed**.
- Full `odin/` suite in the MNT-255 sandbox (SQLite + locmem cache, no Redis) → 503 passed,
  7 failed — all `test_sensor_logs` cases failing with `DISTINCT ON fields is not supported by
  this database backend`, i.e. the Postgres-only `SensorLogManager.current()`, unrelated to this
  change. That run predates the rewrite; the failure mode is the backend, not the feature.
- `ruff check`, `ruff format --check`, `ty check`, `manage.py makemigrations --check`, `manage.py
  check` → clean.
- The 2026-10-26 rewrite itself: the unstaged draft measured **98 failed / 107 passed** across the
  relay and boiler-mode tests; see [[2026-10-26-relay-target-state-antifreeze-review]].

> CI (`make test`) runs the same tests on Postgres, so the PostgreSQL numbers are the ones that
> count.

---

## Follow-ups

- The dashboard has no UI for `override_schedule`; the existing MNT-217 schedule modal still edits
  only `context["schedule"]`, so overrides are API/admin-only for now.
- `target_temp` is not supported in override periods by design. If a timed setpoint override is
  needed later, extend `RelayOverridePeriodSerializer` and the service rule together.
- The override is state-only, not a latch: once the period ends the relay returns to the normal
  weather/cycle/schedule answer on the next read.

## References

- Related: [[2026-09-22-mnt-217-relay-schedule-component]] — the regular `schedule` context and its
  validation, reused here
- Related: [[2026-09-23-relay-mode-compute-on-read]] — why `mode` is computed rather than trusted
- Related: [[2026-10-15-mnt-250-schedule-cycle-rule]] — the `CYCLE` rule the override outranks
- Related: [[2026-10-22-mnt-253-midseason-humidity-wind-research]] — the 10/17 band re-baselined here
- External: Linear MNT-255
- External: [Linear MNT-259](https://linear.app/mnt/issue/MNT-259/override-by-schedule) — the
  follow-up ticket that re-ran the same plan and verified it on PostgreSQL
