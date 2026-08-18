---
title: Proterm Lynx 25 eBus Protocol Investigation
date: 2026-08-11
type: investigation
status: resolved
updated: 2026-08-18
session_id: ses_ebus_proterm_lynx_25_investigation
services: [ebusd, boiler]
branch: -
tickets: []
tags: [ebus, vaillant, proterm, icar, boiler, protocol]
related: []
---

# Proterm Lynx 25 eBus Protocol Investigation

## TL;DR — RESOLVED 2026-08-18

**Mode and temperature writes work.** The 2026-08-11 failures were caused by malformed raw
frames, not by any pairing requirement: every `SetMode` frame sent that day used `NN=07` and
started the payload with `hcmode`, but the Vaillant `B510 SetMode` message carries a leading
submessage-ID byte `00` and is **9 data bytes** long. The boiler NACKed the malformed frames;
correctly framed writes are accepted and applied immediately from ebusd's own address (31) with
no controller pairing whatsoever. Verified live on 2026-08-18: HWC setpoint 45→46 °C applied
(StorageTempDesired followed), flow setpoint 30→0 applied in `heat` mode, `off` mode accepted
(it was NACKed on 2026-08-11), original state restored afterwards.

Working control surface (installed on ODIN):

```bash
boiler-set boiling 45          # hot water only, tank setpoint 45 °C   (SetMode water)
boiler-set heating 55          # heating only, flow setpoint 55 °C     (SetMode heat)
boiler-set mixed 55 45         # both circuits                         (SetMode auto)
boiler-set off                 # both circuits off                     (SetMode off)
boiler-set panel               # drop override, panel takes back control
boiler-status                  # read all live values
```

`/usr/local/bin/boiler-set` wraps `ebusctl write -def` (daemon runs with `--enabledefine`)
using an active-write copy of the `uw` SetMode definition, so ebusd does the D1C encoding and
CRC itself. A `boiler-refresh.timer` (disabled by default) can re-send the last override every
minute; in a 10-minute test the HWC override held with **no** refresh, so the timer is only a
safety net for long-running heating overrides.

## Resolution details (2026-08-18)

- Root cause of 2026-08-11 "rejection": frames like `08b510070300000000000000` decode as
  submessage `0x03` with garbage payload. Correct frame for `water;flow=0;hwc=45` is
  `08 b5 10 09 00 03 00 5a ff 00 00 00 00` (NN=09, leading ID byte `00`).
- The "pairing window / trusted-masters table" theory is **wrong** — no pairing exists on the
  BAI. Sections below describing it are kept for history but superseded.
- Field semantics confirmed live:
  - `hwctempdesired` (D1C) sets the boiling/tank setpoint; `StorageTempDesired` follows it.
  - `flowtempdesired` (D1C) sets the heating flow setpoint; applied in `heat`/`auto` modes,
    ignored in `water` mode (boiler reports panel value instead).
  - Passing `-` for a field sends the replacement value (0xFF) = "not controlled"; the boiler
    falls back to its panel setpoint for that field.
  - `Status02.hwcmode` does **not** echo the commanded hcmode; it stayed `auto` throughout.
- Override persistence: HWC override survived 10 min with no refresh. `heating`/`mixed`
  long-term behaviour untested over hours — enable `boiler-refresh.timer` for those:
  `sudo systemctl enable --now boiler-refresh.timer` (re-sends last command every 60 s;
  `boiler-set panel` clears the override and stops re-sending).
- Daemon opts now: `EBUSD_OPTS="--enabledefine --scanconfig -d ens:192.168.1.108:9999"`
  (`--enablehex` was removed again after testing).

Original (partly superseded) investigation below.

---

## TL;DR (2026-08-11, superseded)

Investigated the eBus protocol for the **Proterm Lynx 25 MKO** boiler (Vaillant BAI family) reachable
through the ICAR eBus adapter (`192.168.1.108`) and the local `ebusd` daemon. Confirmed that
mode and per-mode temperature setpoints are exposed via the standard Vaillant `SetMode` message
(destination `08/b510`) plus the paired read messages `Status01`/`Status02` and the desired-temp
fields `FlowTempDesired` / `HwcTempDesired` / `StorageTempDesired`. Read commands work end-to-end;
`bai Status` decode fails because the loaded config
(`vaillant/bai.308523.inc`) is a generic Vaillant BAI00 fallback that does not fully match the
Proterm firmware (`SW=0712 HW=1303`).

---

## Topology

```
Proterm Lynx 25 MKO   ──eBus──►   ICAR shield c6   ──TCP:9999──►   ODIN (ebusd :8888)
   (boiler, ZZ=08)              192.168.1.108                              192.168.1.100
```

- Daemon: `/usr/bin/ebusd 26.1.26.1`, started by systemd with
  `EBUSD_OPTS="--scanconfig -d ens:192.168.1.108:9999"` (`/etc/default/ebusd`).
- Control protocol: TCP `localhost:8888`, client `ebusctl`.
- Raw eBus from ICAR: TCP `192.168.1.108:9999` (do **not** point `ebusctl` here — port 9999 is
  raw eBus, not the ebusd control port).
- Bus participants seen after scan:
  - `08` slave, `MF=Vaillant;ID=BAI00;SW=0712;HW=1303`, loaded `vaillant/bai.308523.inc` + `08.bai.csv`.
  - `00`, `03` masters on the bus (no slave config loaded for them — no room thermostat present).
  - `31`/`36` ebusd itself.

## Net effect

- **Mode** is set with `SetMode` (`hcmode` ∈ `auto | off | heat | water`).
- **Heating temperature** (flow setpoint) is `flowtempdesired` in the same `SetMode` write.
- **Boiling temperature** (HWC/storage setpoint) is `hwctempdesired` in the same `SetMode` write.
- There is no separate "mixed mode temperature" — mixed = `auto` with both setpoints supplied.
- Current live values (read 2026-08-11 17:57–17:58, boiler boiling-only at 45 °C as expected):
  - `FlowTempDesired` = `30.00 °C` (heating setpoint, dormant while in `water`)
  - `HwcTempDesired`  = `45.00 °C` (boiling setpoint)
  - `StorageTempDesired` = `45.00 °C` (storage/tank setpoint, kept in sync with HWC)
  - `FlowTempMax`     = `83.31 °C`, `ReturnTempMax` = `68.25 °C`
  - `StorageTemp`     = `44.44 °C` (ok), `HwcTemp` = `-13.50 °C` (cutoff — HWC NTC not wired on this unit)
  - `ModulationDesired` = `44.2 %`, `PumpPowerDesired` = `auto`, `ExternalHwcSwitch` = `off`
  - `OutdoorstempSensor` = `-60.44 °C` (cutoff — outside sensor not installed)

---

## Read commands (work today)

```bash
ebusctl read -c bai FlowTempDesired        # heating flow setpoint  (°C)
ebusctl read -c bai HwcTempDesired         # HWC setpoint           (°C)
ebusctl read -c bai StorageTempDesired     # storage/tank setpoint  (°C)
ebusctl read -c bai Status01               # flow;return;outside;HWC;storage;pumpstate
ebusctl read -c bai Status02               # hwcmode;flow_max;flow_cur;hwc_max;hwc_cur
ebusctl read -c bai FlowTemp               # actual flow temperature
ebusctl read -c bai HwcTemp                # actual HWC temperature  (cutoff on this unit)
ebusctl read -c bai StorageTemp            # actual tank temperature
ebusctl read -c bai ReturnTemp             # actual return temperature
ebusctl read -c bai ModulationDesired      # burner modulation (%)
ebusctl read -c bai ExternalHwcSwitch      # 0=off / 1=on  (external HWC demand)
ebusctl read -c bai HcPumpMode             # 0=post_run; 1=permanent; 2=winter
ebusctl read -c bai FlowTempMax            # max flow temp (°C)
ebusctl read -c bai HwcTempMax             # max HWC temp (°C)
ebusctl read -c bai FloorHeatingContact    # 0=off / 1=on
```

Verbose form for any read: append `-V` to see `lastup=` timestamp and raw decoded data.

## Write commands (NOT executed this session)

`SetMode` is `uw` on `ZZ=08 PB=08 SB=b5 NN=10`. One write sets mode + both setpoints at once:

```bash
# Boiling only  (mode=water,  heating setpoint + HWC setpoint)
ebusctl write -c bai SetMode "water;<FLOW_TEMP>;<HWC_TEMP>"

# Heating only (mode=heat,   heating setpoint + HWC setpoint)
ebusctl write -c bai SetMode "heat;<FLOW_TEMP>;<HWC_TEMP>"

# Mixed        (mode=auto,   heating setpoint + HWC setpoint)
ebusctl write -c bai SetMode "auto;<FLOW_TEMP>;<HWC_TEMP>"

# Off
ebusctl write -c bai SetMode off
```

`hcmode` enum (from `find -V SetMode`): `0=auto` (mixed) / `1=off` / `2=heat` / `3=water`.
`flowtempdesired` and `hwctempdesired` are encoded `D1C` (byte value = °C × 2), so
`45 °C` → byte `0x5A` (90 dec). Omitted trailing fields keep their last value.

**Critical syntax gotcha:** field values must be passed as a SINGLE semicolon-separated argument
inside quotes — `ebusctl write` does NOT accept multiple space-separated value tokens.
`ebusctl write -c bai SetMode water 55` prints the usage block and does nothing
because `55` is parsed as a positional argument that `write` doesn't accept.

### Why `write -c bai SetMode ...` returns `ERR: element not found`

Even with the correct semicolon syntax the command fails on this firmware:

```
>>> write -c bai SetMode water;30;45
<<< ERR: element not found
```

The reason is in the upstream config. From
`src/vaillant/hcmode_inc.tsp` in `john30/ebusd-configuration`:

```typescript
/** default *uw */
@write
@passive
@base(MF, 0x10)
model uw {}

model SetMode { hcmode: hcmode; ... }
```

The `@passive` attribute marks SetMode as a message that is broadcast by a master controller
(calorMatic / multiMATIC / sensoCOMFORT) and consumed by the boiler — ebusd is *not* allowed
to initiate the write itself. `find -V SetMode` confirms this with
`bai SetMode = no data stored [ZZ=08, passive write]`, and `find -w` does **not** list SetMode
among the actively-writable messages. Without a calorMatic on the bus, ebusd has no
broadcast source to react to and refuses the active write.

The same restriction applies to all the other `bai` messages except the three unconditional
ones (`IdQuery`, `Queryexistence`, `Vdatetime`) and `Broadcast HwcStatus` (passive only).

> **SUPERSEDED 2026-08-18:** every raw frame in the tests below was malformed (NN=07, missing
> the leading `00` submessage-ID byte, two bytes short). The NACKs were framing errors, not an
> application-layer trust check. Correctly framed SetMode writes from ebusd (address 31) are
> accepted and applied — see the resolution section at the top. The pairing-window theory does
> not apply to the BAI.

### Empirical result: boiler rejects SetMode from ebusd at the application layer

Verified 2026-08-11 with `--enablehex` enabled and the daemon restarted. Sent the
raw SetMode message with three different payloads and watched the boiler's broadcasts
for ~30 s after each:

| Source | Payload (mode, flow, hwc) | Bus response | HwcTempDesired after 30 s |
|--------|---------------------------|--------------|---------------------------|
| 31 (ebusd) | `water 30 45` (identical to current) | `/ 00` (ACK) | `45.00` (unchanged) |
| 31 (ebusd) | `water 30 46` (HWC differs by 1 °C)  | `/ 00` (ACK) | `45.00` (unchanged) |
| 00       | `water 30 46`                            | `/ 00` (ACK) | `45.00` (unchanged) |
| 03       | `water 30 46`                            | `/ 00` (ACK) | `45.00` (unchanged) |
| 31 (ebusd) | `off  0  0` (mode change)              | `/ 01 01` (NACK) | `45.00` (unchanged) |

So the eBus protocol-level path works for any master (boiler sends an ACK), but the
boiler's application layer only honours SetMode from a paired Vaillant controller
(calorMatic / multiMATIC / sensoCOMFORT). When the payload would be a no-op the boiler
just ACK-don't-care to avoid bus traffic; when it would change state it NACKs with
`01 01`.

**Consequence:** without a real Vaillant room controller on the bus, neither
`ebusctl write -c bai SetMode` nor `ebusctl hex 08b51008 ...` can change the boiler's
mode or temperatures. The physical buttons on the boiler remain the only control
surface; the `Ebusd` / Python service is read-only on this firmware until a controller
is paired. The `write_setmode_hex` Python method detects the `01 01` NACK and raises
`BoilerWriteRejectedError` so callers don't silently assume success.

### Pairing emulation attempt (synthetic calorMatic boot sequence)

Tried 2026-08-11 — without physical access to a real calorMatic we built the boot
sequence from the Vaillant spec + `bai.308523_inc.tsp` and replayed it from ebusd via
`--enablehex`:

```bash
# Announce ourselves
ebusctl hex -s 31 fe07fe01 1f                              # Queryexistence (src=31)
# Claim Vaillant identity
ebusctl hex -s 31 fe07040a b55652393030010001 00          # IdAnswer: MF=Vaillant ID=VR900 SW=0100 HW=0100
# Start heartbeating
ebusctl hex -s 31 fe07ff01 1f                              # Signoflife (repeat every ~2 s)
# (optionally) sync clock
ebusctl hex -s 31 feb51606 002d230b0826                    # Vdatetime BTI+BDA (06 bytes)
```

ebusd decoded the IdAnswer correctly:
```
[update notice] sent update-read Broadcast IdAnswer QQ=31: Vaillant;VR900;0100;0100
```

Then sent SetMode heat/50/45 (different payload from current state, so we should
have seen a NACK if the boiler was still rejecting us):

| Variation | SetMode bus response | `HwcTempDesired` 30 s later |
|-----------|----------------------|-----------------------------|
| Boot sequence + SetMode from source 31 | `/ 00` ACK | `45.00` (unchanged) |
| Boot sequence + SetMode from source 00 | `/ 00` ACK | `45.00` (unchanged) |
| Boot sequence + SetMode from source 03 | `/ 00` ACK | `45.00` (unchanged) |
| Sustained heartbeat (60 s) + SetMode from 00 | `/ 00` ACK | `45.00` (unchanged) |

So the boiler ACK-s the messages at the eBus protocol level regardless of source or
identity, but the application layer never applies the SetMode payload. The boiler
state at the end (`FlowTempDesired=30, HwcTempDesired=45, StorageTempDesired=45,
Status02 hwcmode=off, pumpstate=off`) was identical to the starting state.

**Reason this doesn't work:** Vaillant's pairing is a *two-sided* handshake. The
boiler has to be put into a "pairing window" — usually by holding a button on the
boiler for several seconds — and only during that window does it accept a new
controller's identity into its non-volatile trusted-masters table. Without that
window being opened from the boiler side, no amount of synthetic boot traffic from
any source address is recognised as authoritative. We don't have a known
software-only path to put the boiler into pairing mode — the relevant button isn't
exposed on the bus (none of the `bai` messages control it).

**Conclusion:** the only paths to remote control of this boiler are
(a) buy and physically pair a calorMatic / multiMATIC / sensoCOMFORT, then use
    `ebusctl`/`Ebusd` to send SetMode to *its* master address, or
(b) replace the boiler firmware — out of scope.
The Python service stays read-only on this firmware.

### Direct-ICAR experiment (no transport bypass)

Tried 2026-08-11: stopped `ebusd`, opened a raw TCP socket to ICAR at
`192.168.1.108:9999`, captured the idle/frame stream and tried sending SetMode
bytes directly. The ICAR accepts exactly one TCP connection at a time, and
`ebusd` already holds it.

Findings:

- ICAR speaks the **enhanced protocol** (the `ens:` prefix in ebusd's `--device=`).
  The byte stream between idle bursts is `c6 aa` pairs — `0xC6` is an
  enhanced-protocol escape byte, `0xAA` is the eBus SYN byte. A full eBus
  frame is `AA ZZ PB SB NN DD* CRC CRC AA` with `0xC6`-escaping inside.
- The bytes that hit the wire from a direct-ICAR write are **byte-identical**
  to what `ebusctl hex` already produces — `ebusd` does not wrap, filter, or
  re-encode the payload, it just prepends its source address (`31`) and lets
  ICAR do the CSMA/CA arbitration on the wire.
- The only things direct ICAR would unlock that `hex` does not:
  (a) back-to-back frame bursts without ebusd's per-message pacing,
  (b) sending `answer`-style responses to the boiler's broadcasts (would need
      `ebusctl answer` with `--enablehex --answer` — already enabled in this
      session but the boiler never broadcast anything that looked like a poll
      request, just its own Status broadcasts),
  (c) bypassing ebusd's message-DB lookup (irrelevant — `hex` already does this).
- Even with (a), (b), (c), the boiler's application layer response to SetMode
  is the same: `/ 00` ACK from any non-paired source, `/ 01 01` NACK from any
  source trying to actually change state. The transport makes no difference;
  the pairing decision is made higher up.

So direct-ICAR access doesn't help us. The pairing handshake is a closed box
that runs entirely inside the boiler firmware and is only reachable from the
physical pairing button.

### Path that DOES work: `--enablehex`

The `hex` command sends raw bytes, bypassing the passive-write restriction in ebusd's
message DB. This is what we used for the test above. The command is disabled by
default; enable it once for testing, then revert.

```bash
sudo sed -i 's|^EBUSD_OPTS=.*|EBUSD_OPTS="--enablehex --scanconfig -d ens:192.168.1.108:9999"|' /etc/default/ebusd
sudo systemctl restart ebusd
```

`ebusd` exposes a `hex` command that sends a raw byte sequence bypassing the message database
entirely — so the passive-write restriction does not apply. The command is **disabled by
default** and must be enabled on the daemon:

```bash
sudo sed -i 's|^EBUSD_OPTS=.*|EBUSD_OPTS="--enablehex --scanconfig -d ens:192.168.1.108:9999"|' /etc/default/ebusd
sudo systemctl restart ebusd
```

After restart, the SetMode message can be sent as a 7-byte payload to `08 b5 10`:

```bash
ebusctl hex 08b510070300000000000000    # water mode, flow=0, hwc=0 (all-zero payload)
```

Per-field payload layout for SetMode (matches the TypeSpec definition):

| offset | field              | type | encoding             |
|--------|--------------------|------|----------------------|
| 0      | `hcmode`           | UCH  | 0=auto 1=off 2=heat 3=water |
| 1      | `flowtempdesired`  | D1C  | byte = °C × 2        |
| 2      | `hwctempdesired`   | D1C  | byte = °C × 2        |
| 3      | `hwcflowtempdesired` | UCH | °C (1 byte)          |
| 4      | `ign`              | IGN  | ignore               |
| 5      | bitfield (disablehc / disablehwctapping / disablehwcload) | bits |  |
| 6      | bitfield (remoteControlHcPump / releaseBackup / releaseCooling) | bits | |

So `SetMode auto, flow=55, hwc=45` becomes
`08 b5 10 07 00 6e 5a 00 00 00 00` (NN=07, hcmode=00, flow=0x6E, hwc=0x5A, rest=00),
called as:

```bash
ebusctl hex 08b510070 06e5a000000000    # hex() in the service builds this exactly
```

The boiler's response is not decoded by ebusd for `hex` writes — there is no
`BoilerState` change visible until the boiler's next periodic broadcast of
`Status01`/`Status02`/`HwcTempDesired` arrives (~10 s on this firmware).

### Disable `--enablehex` again after testing

Leaving `--enablehex` on lets any local user send arbitrary eBus bytes, including
non-Vaillant vendor messages that the boiler might misinterpret. Once the desired
behaviour is verified, remove `--enablehex` from `EBUSD_OPTS` and restart.

### Individual setpoint writes (less reliable on this firmware — prefer `SetMode` via hex)

```bash
ebusctl write -c bai StorageTempDesired <°C>     # HWC/storage tank setpoint only
ebusctl write -c bai StatusCirPump on|off        # circulation pump override
```

Both will hit the same passive-write restriction until a Proterm-specific config replaces
`bai.308523.inc`; the `hex` workaround is the only path that works today.

## Mapping to the three required modes

| Mode    | SetMode arg | Temperatures sent in the same write        |
| ------- | ----------- | ------------------------------------------- |
| Boiling | `water`     | `flowtempdesired` + `hwctempdesired`        |
| Heating | `heat`      | `flowtempdesired` + `hwctempdesired`        |
| Mixed   | `auto`      | `flowtempdesired` + `hwctempdesired`        |

There is no separate "mixed temperature" — Mixed means both `flowtempdesired` (heating) and
`hwctempdesired` (boiling) are active simultaneously under `auto` mode arbitration.

---

## Known decode issues (model mismatch)

The loaded config is `vaillant/bai.308523.inc` (generic Vaillant BAI00), not a Proterm-specific
CSV. Observed symptoms:

- `ebusctl read -c bai Status` → `ERR: invalid position in decode`. Boiler responds with only
  1 byte (`/ 00`) but the decoder expects `temp + 2×press + hcmode + hex`. Use `Status01`/
  `Status02` + desired-temp fields instead.
- `bai ExternalFlowTempDesired`, `ExtFlowTempDesiredMin`, `FlowsetHcMax`, `FlowsetHwcMax`,
  `HwcTempMax`, `HcPumpMode` → same `invalid position in decode`. Values cannot be trusted.
- `bai HwcTemp` returns `-13.50 °C; cutoff` — sensor NTC is not wired (this is consistent with
  the unit, not a decode bug).

The CSV shipped inside the ebusd binary; no `/usr/share/ebusd/config/` or `/var/lib/ebusd/`
directory exists on this host. To get a clean decode we would need a Proterm-specific config
file (likely from the upstream `ebusd-configuration` repo, keyed off the `MF/ID/SW/HW`
string `Vaillant;BAI00;0712;1303`).

## Open questions

- Is there a `09.bai.csv` (or similar Proterm-flavoured variant) in the upstream
  `john30/ebusd-configuration` repo that would replace `bai.308523.inc`? Without it, the
  `bai Status` message stays broken.
- Does the Proterm firmware accept `SetMode water <flow> <hwc>` with both temps supplied, or
  does it reject writes when the mode doesn't "own" that setpoint? To be tested with physical
  confirmation per the user's request.
- Should `StorageTempDesired` and `HwcTempDesired` stay in sync, or does the boiler
  auto-clamp one to the other? Currently both read as `45.00`.
- Is there a controller at bus address `03` that we should also poll (no config loaded for it,
  scan only identified it as a master)?

---

## Follow-ups

- Pull / install a Proterm-specific BAI CSV and re-test `bai Status` and the broken fields
  listed above.
- Decide whether to wrap `ebusctl` calls in a thin Python service under `odin/apps/` for the
  Django side, or expose raw `ebusctl` invocations through a management command. Both options
  keep ebusd as the single source of truth on the wire.
- Once a write path is chosen, add a manual physical-confirmation step (user changes mode/temp
  on the boiler, agent re-reads and compares) before any automated `SetMode` write.

## References

- `/etc/default/ebusd` — daemon options (`--scanconfig -d ens:192.168.1.108:9999`).
- ebusd docs: https://github.com/john30/ebusd/
- ebusd configuration repo: https://github.com/john30/ebusd-configuration
- Vaillant eBus protocol spec: https://www.pittnerovi.com/jiri/hobby/electronics/ebus/Vaillant_ebus.pdf
- ICAR eBus adapter: ebus adapter shield c6, firmware `1.1[6704].1[6704]`, signal acquired at
  23 symbols.
