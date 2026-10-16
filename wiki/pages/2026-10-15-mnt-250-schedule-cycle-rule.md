---
title: 'MNT-250 spec review — schedule cycle rule'
date: '2026-10-15'
type: investigation
status: resolved
session_id: ses_ebf751bfcffeiEqITts04JPY14
services: [relays-services, test_relays, AGENTS]
branch: master
tickets: [MNT-250]
tags: [relays, midseason, schedule, pump, servo, spec-review, mode]
related: [2026-10-11-midseason-pump-cadence-30min, 2026-09-19-mnt-215-midseason-mode,
  2026-09-23-relay-mode-compute-on-read, 2026-09-22-mnt-217-relay-schedule-component]
---

# MNT-250 spec review — schedule cycle rule

## TL;DR

Reviewed the MNT-250 ticket against the code and found it was not buildable as written: the title described
already-implemented behaviour, two "Additional Rules" bullets contradicted the description and each other, one rule
ended in a question mark, and the servo guard precedence was unstated. After five decisions from the author the
ticket became an **additive rule in the schedule branch only** — a 30-minute-every-2-hours forced window with a new
`RelayMode.CYCLE` — leaving midseason untouched. Implemented later the same day on
`opencode/feature/mnt-250-schedule-cycle-rule`: 666 tests pass.

## Net effect

Implemented on `opencode/feature/mnt-250-schedule-cycle-rule` (not committed as of this update):

- **Midseason is untouched** — same band `8 < t < 15`, same `hour >= 6` night guard, same results.
- **New cycle rule in the schedule branch** — `hour % 2 == 0 and minute < 30`, half-open `[H:00, H:30)` on even
  local hours, anchored at local midnight. Inside the window the pump is `(ON, CYCLE)` and the servo `(OFF, CYCLE)`;
  outside it, the regular schedule result.
- **New `RelayMode.CYCLE`**, which required an `AlterField` migration (`choices` change on `Relay.mode` and both
  `RelayLog.mode` columns).
- **One existing test moved** (it probed the 12:00 period boundary, now inside the cycle window), and the module
  got an autouse clock fixture because several tests had been time-independent by accident.
- **666 tests pass** (`odin/` + `mcp_server/tests/`).

## Gaps found in the original spec

1. **The title described shipped behaviour.** "Override midseason rules over schedule" — the midseason branch is
   already evaluated *before* the schedule lookup in both methods:

   **File:** `odin/apps/relays/services.py:97-101`

   ```python
   elif 8 < outside_temp < 15:
       # Midseason mode, should work for 30 minutes every 2nd hour, but not at night
       if self.now.hour >= 6 and self.now.hour % 2 == 0 and self.now.minute < 30:
           return RelayState.ON, RelayMode.MIDSEASON
       return RelayState.OFF, RelayMode.MIDSEASON
   ```

   The only thing not yet implemented was the *outside-window* fall-through — the opposite of "override".

2. **`"lower than 15 degree of Celcius"` was a landmine.** Read literally it widens midseason to `-8…15 °C` and
   deletes the schedule + `FALLBACK ON` net the pump currently has in `-8…8 °C`, replacing it with 2.5 h/day of
   circulation in freezing weather. Confirmed with the author: the `> 8` lower bound **stays**, band remains
   `8 < t < 15`.

3. **"Servo outside the window — fall back to the schedule" contradicted "always open".** A servo has no
   30-minute window, so the bullet would have reverted most of [[2026-09-19-mnt-215-midseason-mode]] — the servo
   would return to target-temp regulation nearly all day.

4. **"Pump outside the window … midseason only forces `ON` for 30 minutes every 2 hours?"** ended in a question
   mark, i.e. was never decided.

5. **The "Night guard" bullet contradicted itself** — it dropped the `hour >= 6` guard and then re-added it for
   schedule mode in the same sentence.

6. **Servo guard precedence was unstated.** These two guards run *before* the midseason branch, and the pump guard
   reads the pump's **persisted** `state`, so "midseason always opens the servo" could never hold while its pump
   was off:

   **File:** `odin/apps/relays/services.py:113-119`

   ```python
   if not sensor or not sensor.is_alive or sensor.temp is None:
       return RelayState.OFF, RelayMode.UNKNOWN
   if related_relay := self.relay.related_relay:
       if related_relay.is_pump and not related_relay.is_on:
           return RelayState.OFF, RelayMode.IGNORED
   ```

7. **`"only for active state (for servos this is OFF)"`** — ambiguous wording, dropped from the spec.

## Final specification

Evaluated in the schedule branch, i.e. after every higher-priority rule has declined. Precedence is unchanged:

1. `force_state` → `(force_state, FORCED)` — `services.py:152-154`
2. servo: no sensor / not alive / `temp is None` → `(OFF, UNKNOWN)` — `services.py:113-114`
3. servo: related pump off → `(OFF, IGNORED)` — `services.py:117-119`
4. `t >= 15` → `SUMMER`
5. `t < -8` → `ANTIFREEZE`
6. `8 < t < 15` → `MIDSEASON`, **unchanged including its night guard** — `services.py:97-101`, `services.py:130-132`
7. schedule branch → **new cycle rule** inside the window, regular schedule outside it

The rule itself:

- **Window** — no night guard; midseason's `hour >= 6` is deliberately *not* copied:
  `hour % 2 == 0 and minute < 30` → 00:00–00:30, 02:00–02:30 … 22:00–22:30.
- **Pump** inside → `(ON, CYCLE)`, overriding both the period `target_state` (`services.py:104-106`) and the
  `(ON, FALLBACK)` default (`services.py:108`).
- **Servo** inside → `(OFF, CYCLE)`, overriding target-temp regulation (`services.py:136-150`).
- Outside the window → the regular schedule result, unchanged.
- Applies when weather data is missing or `temp is None` too, since the rule is time-based — note
  `WeatherManager.current()` falls back to the last row regardless of age
  (`odin/apps/weather/models.py:15-21`).

## Decisions taken

- **New `RelayMode.CYCLE`** rather than reusing `BASIC`, because the schedule is being *overridden* rather than
  followed and the audit trail should show it. Requires an `AlterField` migration.
- **The cycle covers the `FALLBACK` path** as well as a matching period — the rule is time-based. The resulting
  *state* is identical either way (pump `FALLBACK` is already `ON`, servo `FALLBACK` is already open); only the
  reported mode differs.
- Midseason untouched; band, night guard and results preserved.

## Consequences worth noting

- **Night behaviour flips meaning.** Because the night guard is not copied, 00:00–05:59 is no longer "hard `OFF`"
  the way midseason is — it is whatever the schedule says, except that the pump runs 00:00–00:30. Confirmed as
  intended.
- **`mode` flaps.** A relay in the schedule branch alternates `CYCLE` / `BASIC` / `FALLBACK` every 30–90 min.
  Reads are pure (`Relay.get_target_state()` does not persist), so there is no `RelayLog` churn, but the dashboard
  tooltip shows the raw mode (`frontend/src/components/tile/Esp8266SensorsTile.tsx:25`) and `perform_update`
  publishes whichever pair the clock produced (`odin/api/v1/relays/views.py:77`).
- **Cross-service — verified, no change needed in coruscant.** `mode` is a public contract that travels to coruscant
  in the `RELAY_STATE_UPDATE` envelope and is echoed back; ODIN persists it only when it is a valid `RelayMode`
  (`odin/apps/relays/models.py:156`). Coruscant keeps no enum: `Relay` is a plain `NamedTuple` with
  `mode: str | None` (`coruscant/models.py:4-7`) and `redis_bus.py:116` copies the value into the envelope verbatim,
  so `CYCLE` needs no mirror on that side. The shared enums in the umbrella `AGENTS.md` (`MessageType`,
  `PartitionKey`) are unaffected — this is an additive relay-mode value, not a broker-level contract change.
- **The override only bites where the schedule says `OFF`.** An all-day `ON` period gains nothing but a different
  reported mode.

## Test impact

> **Superseded** — see [Update — 2026-10-15 17:45](#update--2026-10-15-1745). The claim below that nothing existing
> breaks was wrong: one test had to move, and the module needed an autouse clock fixture.

Predicted impact. Everything covering midseason and the higher-priority guards is insensitive to a rule
that only fires in the schedule branch:

- midseason — `odin/tests/models/test_relays.py:338`, `:390`, `:420`, `:445`, `:474`
- `SUMMER` / `ANTIFREEZE` — `:320`, `:329`, `:364`, `:377`
- plus every `FORCED`, `UNKNOWN` and `IGNORED` test

New cases: pump window overriding an `OFF` period; pump window with no matching period (`CYCLE` instead of
`FALLBACK`); pump outside the window; servo window while the sensor is below `target_temp` (which would otherwise be
`ON, BASIC`); servo window with no matching period; servo outside the window; hours 0–5; minute boundaries 29/30 and
odd/even hours; weather missing or `temp is None`; band edges `-8` / `8` / `15`; `force_state` still winning.

The tests patch `odin.apps.relays.services.timezone.localtime`, which covers both `self.now` (set in `__init__`,
`services.py:65`) and the schedule lookup (`services.py:72`) — any new test must keep patching the same symbol.

---

## Update — 2026-10-15 17:45

Implemented the rule. Branch `opencode/feature/mnt-250-schedule-cycle-rule`, nothing committed yet.

### `RelayMode.CYCLE`

**File:** `odin/apps/relays/models.py:45`

```python
SUMMER = "SUMMER", _("Summer")
MIDSEASON = "MIDSEASON", _("Midseason")
BASIC = "BASIC", _("Basic")
CYCLE = "CYCLE", _("Cycle")
ANTIFREEZE = "ANTIFREEZE", _("Antifreeze")
```

Migration `odin/apps/relays/migrations/0011_alter_relay_mode_alter_relaylog_new_mode_and_more.py` —
three `AlterField` operations (`Relay.mode`, `RelayLog.new_mode`, `RelayLog.old_mode`), choices only,
no data migration needed. `refresh_state()` and the consumer validate against `RelayMode.values`, so
they accept `CYCLE` without further changes.

### The rule

**File:** `odin/apps/relays/services.py:67-73`

```python
def is_cycle_window(self) -> bool:
    """Whether the relay must be forced into its open circuit position for the current cycle slot.

    A half-open [H:00, H:30) on even local hours, anchored at local midnight. Unlike midseason
    there is no night guard: the cycle runs around the clock.
    """
    return self.now.hour % 2 == 0 and self.now.minute < 30
```

Called once per branch, after the temperature bands and before the schedule lookup:
`return RelayState.ON, RelayMode.CYCLE` for the pump (`services.py:111-113`) and
`return RelayState.OFF, RelayMode.CYCLE` for the servo (`services.py:146-148`). Midseason's
predicate at `services.py:105-109` is untouched.

### Tests

One existing test had to move: `test_relays__periodic_schedule_end_time_belongs_to_next_period`
probed the 12:00 period boundary, which is an even hour with `minute == 0` and therefore now lands
inside the cycle window. Its periods were shifted to a 11:00 boundary so it still tests an exact
`start_time`/`end_time` edge without the cycle masking it. **Lesson: the cycle window fires at
`12:00`, `14:00`, … so any schedule test probing an even hour at `:00`–`:29` will now see `CYCLE`.**

A second, bigger problem: several tests never pinned the clock at all (the whole
`TestRelaysServoTargetState` class and `test_relays__target_state_returns_servo_state_for_servo_type`).
They passed only because they reached the schedule branch, which used to be time-independent — with
the cycle they would have failed whenever the suite ran between 00:00–00:30, 02:00–02:30 and so on.
Fixed with a module-level autouse fixture rather than per-test patches:

```python
OUTSIDE_CYCLE_WINDOW = datetime(2025, 1, 6, 10, 30, 0, tzinfo=dt_timezone(UTC.utcoffset(datetime.now(UTC))))


@pytest.fixture(autouse=True)
def pin_clock_outside_cycle_window():
    """Keep the schedule branch out of the cycle window unless a test says otherwise."""
    with patch("odin.apps.relays.services.timezone.localtime", return_value=OUTSIDE_CYCLE_WINDOW):
        yield
```

New `TestRelaysScheduleCycle` class, 24 cases: pump/servo inside and outside the window, with and
without a matching period, `CYCLE` instead of `FALLBACK`, every even hour including 0/2/4, every
odd hour, minutes 0/10/29 vs 30/45/59, missing weather, band edges (`15.0` → `SUMMER`, `8.1` →
`MIDSEASON`, `8.0` → `CYCLE`, `-8.1` → `ANTIFREEZE`, `-8.0` → `CYCLE`), midseason keeping its night
guard at 03:05, and `FORCED` / `UNKNOWN` / `IGNORED` still taking precedence.

### Docs

`AGENTS.md:246` now documents both rules side by side and warns that midseason's night guard is
deliberately *not* the cycle's.

---

## Update — 2026-10-16 10:56

Implementation finished and verified; nothing committed. Final state of `opencode/feature/mnt-250-schedule-cycle-rule`:

- **Modified** — `AGENTS.md`, `odin/apps/relays/models.py`, `odin/apps/relays/services.py`,
  `odin/tests/models/test_relays.py`, `wiki/INDEX.md`, `wiki/.sessions.json`
- **Untracked** — `odin/apps/relays/migrations/0011_alter_relay_mode_alter_relaylog_new_mode_and_more.py`,
  `wiki/pages/2026-10-15-mnt-250-schedule-cycle-rule.md`
- 247 insertions / 6 deletions across the tracked files.

### Verification

- `uv run pytest --ds=odin.settings.test odin/ mcp_server/tests/` → **666 passed** (440 in `odin/`, the rest in
  `mcp_server/tests/`). `odin/tests/models/test_relays.py` alone: 105 passed, up from 66.
- `uv run ruff check .` and `uv run ruff format --check .` → clean, after two automatic fixes: the import block in
  `test_relays.py` (the new fixture sat directly under the last import) and the generated migration, which Django
  writes in single quotes and 120-char lines that Ruff reformats to double quotes and exploded argument lists.
  **Every Django-generated migration in this repo will need `ruff format` after `makemigrations`** — worth knowing
  before the next migration lands.
- `uv run ty check` → all checks passed. `manage.py check --fail-level WARNING --settings=odin.settings.sqlite` → no
  issues. `manage.py makemigrations --dry-run --check` → no changes detected, so migration 0011 is complete.
- `uv run pre-commit run` reported `(no files to check) / Skipped` for every hook: it stashes unstaged changes first,
  and there is nothing staged. Re-run it after `git add` to get real coverage from bandit and pyupgrade.

### Environment note

The test suite needs PostgreSQL and it was **not running** — every DB test errored with
`django.db.utils.OperationalError: connection to server at "localhost" (::1)` before this session started
`brew services start postgresql@18`. `odin/settings/test.py` inherits the Postgres config from `base.py`, so
pytest cannot fall back to the in-memory SQLite used by `odin/settings/sqlite.py` (that one exists for
`make django-checks` only). If the relay tests suddenly all error at once, check `pg_isready` before suspecting
the code.

### Ticket

MNT-250 has an implementation comment listing the two unplanned test findings (the 12:00 boundary test and the
clock-pinning fixture). Status deliberately left at `In Progress` — no commit, no PR, so it does not move to
`In Review` yet.

---

## Follow-ups

- Commit and open the PR; only then move MNT-250 to `In Review`.
- Cross-check whether the real relays carry an all-day `ON` schedule period, in which case the new rule would never
  change their state.
- Consider whether the cycle should ever be exposed per-relay via `context`, like the MNT-217 schedule dict,
  instead of being hardcoded in the service.
- Other test modules that reach the schedule branch without pinning the clock (anything asserting a computed
  `BASIC`/`FALLBACK` on read) inherit the same latent time dependence; only `tests/models/test_relays.py` got the
  fixture.
- Frontend treats `CYCLE` like any other mode (tooltip only). If the cycle should be visually obvious on the
  dashboard tile, that is a follow-up in `Esp8266SensorsTile.tsx`.
- Re-run `uv run pre-commit run` after staging — it skipped every hook last time because the tree was unstaged.

## References

- Linear: https://linear.app/mnt/issue/MNT-250
- Related: [[2026-10-11-midseason-pump-cadence-30min]]
- Related: [[2026-09-19-mnt-215-midseason-mode]]
- Related: [[2026-09-23-relay-mode-compute-on-read]]
- Related: [[2026-09-22-mnt-217-relay-schedule-component]]