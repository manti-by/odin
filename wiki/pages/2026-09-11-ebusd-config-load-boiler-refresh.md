---
title: ebusd lost its device config (boiler reads all failed) + refresh timer disabled
date: 2026-09-11
type: debug
status: resolved
session_id: ses_ebusd_config_refresh_2026_09_11
services: [ebusd, boiler]
branch: -
tickets: []
tags: [ebus, ebusd, vaillant, boiler, systemd, http, config, proterm]
related: [2026-08-11-proterm-lynx-25-ebus-protocol.md]
---

# ebusd lost its device config (boiler reads all failed) + refresh timer disabled

## TL;DR

`boiler_set` "partially worked" because two unrelated things were broken. (1) The long-running
`ebusd` process had lost outbound HTTPS **for over a week** and could no longer download the
Vaillant CSVs, so **no device messages were loaded** — every `read -c bai …` (i.e. all of
`boiler_status`) returned `ERR: element not found`. The write path (`write -def`, config-independent)
still reached the boiler, so writes looked like they worked but nothing could confirm them.
(2) `boiler-refresh.timer` existed on disk but was **disabled**, so nothing re-sent the override.
Fixes: restart ebusd, pin the startup scan to the boiler (`--scanconfig=08`, the broadcast scan
stalls on a phantom address 05), and `enable --now` the timer. Verified live: 230 messages loaded,
`boiler_status` reads real values, timer re-sends `auto;30;45` every 60 s.

---

## Symptom

- `uv run manage.py boiler_set …` appeared to run, but the user wasn't sure it did anything:
  "maybe it's set mode but boiler screen does not show this update or maybe it does not work at all".
- `boiler_status` / `ebusctl read -c bai <field>` returned errors instead of values.

## Step 1 — Bus is healthy, but ebusd has no messages

Talking to ebusd's TCP control port (`localhost:8888`):

```
$ state
signal acquired, 23 symbols/sec (42 max), 3 masters
$ read -c bai FlowTempDesired
ERR: element not found
$ find -c bai .
ERR: element not found
$ info
...
messages: 13
address 00: master #1
address 03: master #11
address 08: slave #11, scanned "MF=Vaillant;ID=BAI00;SW=0712;HW=1303"
address 31: master #8, ebusd
address 36: slave #8, ebusd
```

The boiler **was** scanned and identified, but the `info` line has **no `loaded "vaillant/…"`**
suffix, and only **13 messages** are loaded (a healthy setup has ~230). So the device config never
made it into the daemon → every `bai` field is unknown → `ERR: element not found`.

## Step 2 — Logs: the daemon's HTTP client is dead

`/var/log/ebusd.log`:

```
[main error] HTTP failure, repeating: not connected
[main error] error reading config files from https://ebus.github.io/en/: ERR: element not found
[main error] unable to load scan config 08: list files in vaillant ERR: element not found
[main error] update check connect error          # 5148 occurrences, every ~130 s
```

The `update check connect error` spam goes back at least to **2026-09-04** (the rotated-log
horizon) — the long-running process's outbound HTTPS has been broken for a week+, while the eBUS
side (the ICAR adapter at `192.168.1.108:9999`) stayed fine.

Ruled out the network/URL itself — a **fresh** process on the same host downloads fine:

```bash
ebusd --checkconfig --scanconfig --inject 'FF08070400/0AB5424149303007121303'
# [main notice] read scan config file vaillant/08.bai.csv for ID "bai00", SW0712, HW1303
# [main notice] found messages: 6364 ...
```

So the config service and the file layout are fine; only the **running** daemon was broken.
(Note: passing `-c https://ebus.github.io/en/` is wrong — ebusd appends the language itself and
tries `/en/de/` → 404. Use the default config path.)

## Step 3 — The write path is fine (verify on the wire)

Enabled ebusd raw logging (`raw` command) and re-sent the saved override. The bus log shows the
boiler **accepting** the frame:

```
>3108b5100900003c5aff0000000082<0001019a>00
```

Decoded: `QQ=31 ZZ=08 PBSB=b510 NN=09`, data `00(ID) 00(auto) 3c(30 °C) 5a(45 °C) ff(-) 00 00 00 00`,
CRC `82`; boiler ACKs (`00`), answers `01 01`, CRC `9a`. **No NACK.**

During the chase the leading `00` looked like an extra byte that shifted the temperatures — it is
**not a bug**: it is the `b510` submessage-ID byte, part of the master data before the fields
(matches `b510,00` in `vaillant/08.bai.csv`). Confirmed by encoding to a dead address (05):

```
$ write -d 05 -def <SETMODE_DEF> heat;7;11;-;0;0;0;0;0;0
>3105b5100900020e16ff0000000003
```

i.e. `00(ID) 02(heat) 0e(7×2) 16(11×2) ff(-) …` — byte-perfect. The inline `SETMODE_DEF`
(`odin/apps/boiler/services.py:29`) is layout-identical to the official `08.bai.csv` definition.

## Step 4 — A restart alone doesn't fix it

The startup **broadcast** scan is flaky: it stalls retrying a phantom participant at address `05`
and never probes the boiler:

```
[main notice] starting initial broadcast scan
[main error] scan config 05: ERR: read timeout     # repeated; "scan completed N time(s), check again"
```

The boiler answers a **targeted** scan every time:

```
$ scan 08
08;Vaillant;BAI00;0712;1303
# ... then: read scan config file vaillant/08.bai.csv ... found messages: 230
```

## Step 5 — Refresh timer was never enabled

```bash
$ systemctl is-enabled boiler-refresh.timer
disabled
$ systemctl status boiler-refresh.timer
Active: inactive (dead)
```

`BoilerService.refresh()` (`odin/apps/boiler/services.py:132`) and the docstring explicitly rely on
this timer to keep long-running overrides applied; it was never turned on.

## Root cause

- **ebusd's long-running process lost outbound HTTPS** (≥ 1 week, `update check connect error`
  spam since ≥ 2026-09-04) → it could not download the Vaillant CSVs → **0 device messages** →
  every read failed with `element not found`. Writes use `write -def` with an inline definition,
  which is **config-independent**, so `boiler_set` actually reached the boiler — hence "partially
  works".
- **Startup broadcast scan is unreliable** (stalls on phantom address `05`) → even a plain restart
  didn't deterministically load the config.
- **`boiler-refresh.timer` was disabled** → no periodic re-send of the override.

## Resolution / Fix

1. **Restart ebusd** — fresh HTTP client, config downloads work again.
2. **Pin the startup scan to the boiler** in `/etc/default/ebusd`:

   ```diff
   -EBUSD_OPTS="--enabledefine --scanconfig -d ens:192.168.1.108:9999"
   +EBUSD_OPTS="--enabledefine --scanconfig=08 -d ens:192.168.1.108:9999"
   ```

   Startup is now deterministic:

   ```
   [main notice] ebusd 26.1.26.1 started with single scan on device: 192.168.1.108:9999
   [main notice] starting initial scan for 08
   [bus notice] scan 08: ;Vaillant;BAI00;0712;1303
   [main notice] read scan config file vaillant/08.bai.csv for ID "bai00", SW0712, HW1303
   ```

   `info` then reports `messages: 230` and
   `address 08: …, loaded "vaillant/bai.308523.inc", "vaillant/08.bai.csv"`.
3. **Enable the refresh timer**: `sudo systemctl enable --now boiler-refresh.timer`.

## Verification

```
$ uv run manage.py boiler_status
override:           auto;30;45;-;0;0;0;0;0;0
FlowTempDesired:    30.00  (heating flow setpoint, °C)
HwcTempDesired:     45.00  (hot-water setpoint, °C)
StorageTempDesired: 45.00  (tank setpoint, °C)
FlowTemp:           40.62;ok  (actual flow, °C)
ReturnTemp:         42.94;64848;ok  (actual return, °C)
StorageTemp:        42.56;ok  (actual tank, °C)
ModulationDesired:  20.0  (burner modulation, %)
Status01:           40.5;42.5;-;-;42.5;off  (flow;return;outside;hwc;storage;pump)
Status02:           off;20;75.0;90;60.0  (hwcmode;…)
```

The burner is modulating at 20 % against the commanded 30 °C flow setpoint — the override is
genuinely applied. `boiler_set refresh` logs `sent SetMode auto;30;45;…`; the timer fires every
60 s and logs the same. Zero `connect error` lines after the restart.

### Triage for next time

```bash
ebusctl info | grep -E 'messages|address 08'      # healthy: ~230 messages + loaded "vaillant/…"
sudo grep -E 'unable to load scan config|HTTP failure' /var/log/ebusd.log
systemctl status boiler-refresh.timer             # must be active (waiting)
```

If `messages` is back down to ~12–13, the daemon lost its config again → `sudo systemctl restart ebusd`.

---

## Follow-ups

- The ebusd 26.1 long-runtime HTTP stall is an upstream issue (configs are only fetched at
  startup / scan / `reload`). A periodic ebusd restart (systemd timer) would be a pragmatic guard
  if it recurs; not added this session.
- Phantom participant at address `05` (startup scan stall) is unexplained — most likely the ICAR
  adapter itself answering the `Queryexistence` broadcast but not the ident scan. Sidestepped by
  `--scanconfig=08`.
- An override `auto;30;45` is currently active and re-sent every 60 s; clear it with
  `uv run manage.py boiler_set panel` (or `boiler-set panel`) when the boiler panel should take
  back control.

## References

- Related: [[2026-08-11-proterm-lynx-25-ebus-protocol]]
- Code: `odin/apps/boiler/services.py` (`SETMODE_DEF` line 29, `refresh()` line 132, `_write()` line 186),
  `odin/apps/boiler/management/commands/boiler_set.py`
- System: `/etc/default/ebusd`, `/var/log/ebusd.log`, `boiler-refresh.timer` / `boiler-refresh.service`
- ebusd TCP commands: https://github.com/john30/ebusd/wiki/3.1.-TCP-client-commands
