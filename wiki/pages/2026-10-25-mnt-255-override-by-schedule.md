---
title: 'MNT-255: Override by schedule'
date: '2026-10-25'
type: implementation
status: resolved
session_id: ses_mnt_255_override_by_schedule_2026_10_25
services: [relays, test_relays, AGENTS]
branch: mnt-255-override-by-schedule
tickets: [MNT-255]
tags: [relays, override, schedule, mode, migration, tests]
related: [2026-09-22-mnt-217-relay-schedule-component.md, 2026-09-23-relay-mode-compute-on-read.md,
  2026-10-15-mnt-250-schedule-cycle-rule.md, 2026-10-22-mnt-253-midseason-humidity-wind-research.md]
---

# MNT-255: Override by schedule

## TL;DR

Relays could only be overridden to a hardcoded `force_state`. A new `context["override_schedule"]`
holds time periods with a required `ON`/`OFF` target and, when the current time falls inside one,
it is applied immediately after `force_state` — before the weather bands, the schedule cycle and
the regular `schedule`. The rule reports a new `RelayMode.OVERRIDE` (migration 0012) and works for
pumps, servos and valves. 174 relay tests pass.

## Overview

`force_state` is a single persisted ON/OFF column, so "heat 6:00–8:00" had to be re-entered by hand
every day. The `schedule` context key from MNT-217 is already a list of `start_time`/`end_time`
periods with `target_state`/`target_temp`, but it sits at the *bottom* of the priority chain: a
`SUMMER`/`ANTIFREEZE`/`MIDSEASON` weather band or the MNT-250 cycle window always wins, and valves
are rejected outright. The override is the same period shape promoted to the top of that chain.

Decision order in `RelayTargetStateService.get_target_state()`:

1. `force_state` → `(force_state, FORCED)`
2. **`override_schedule` → `(target_state, OVERRIDE)`** ← new
3. weather bands (`ANTIFREEZE`/`SUMMER`/`MIDSEASON`) or servo `UNKNOWN`/`IGNORED`
4. schedule cycle window → `CYCLE`
5. regular `schedule` period → `BASIC`, else `FALLBACK`

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

The rule sits before the `RelayType` dispatch (`services.py:195`), which is what makes valves work:

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
  feels-like → `MIDSEASON`; 1 m/s → 19.1 °C → `SUMMER`); the raw lower edge test uses `10.0`
  (feels-like 2.4 °C) and still expects `CYCLE`.
- `test_relays__cycle_does_not_leak_into_other_temperature_bands` params became
  `18.0/SUMMER`, `10.1/MIDSEASON`, `10.0/CYCLE` (antifreeze edges unchanged).

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

## Test Results

- `odin/tests/models/test_relays.py` + `odin/tests/api/test_relays.py` → **184 passed**.
- Full `odin/` suite → 503 passed, 7 failed — all `test_sensor_logs` cases failing with
  `DISTINCT ON fields is not supported by this database backend`, i.e. the Postgres-only
  `SensorLogManager.current()`, unrelated to this change.
- `ruff check`, `ruff format --check`, `ty check`, `manage.py makemigrations --check`, `manage.py
  check` → clean.

> The suite was executed against an SQLite + locmem-cache harness because the build sandbox has no
> PostgreSQL or Redis; CI (`make test`) runs the same tests on Postgres.

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
