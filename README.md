<div align="center">

# Q9 — NSA 
### Android Multi-Surface Exploit Framework

**Single-file Android access, harvest and post-exploitation console.**

![python](https://img.shields.io/badge/python-3.8%2B-3776AB?logo=python&logoColor=white)
![host](https://img.shields.io/badge/host-Windows%2010%2F11-0078D4?logo=windows&logoColor=white)
![target](https://img.shields.io/badge/target-Android%205%E2%80%9315-3DDC84?logo=android&logoColor=white)
![transport](https://img.shields.io/badge/transport-ADB%20%7C%20fastboot-2496ED)
![mode](https://img.shields.io/badge/mode-autonomous%20%2B%20manual-8A2BE2)
![selftest](https://img.shields.io/badge/selftest-10%2F10-brightgreen)
![runtime](https://img.shields.io/badge/runtime-stdlib%20only-lightgrey)
![file](https://img.shields.io/badge/artefact-single%20file-informational)
![status](https://img.shields.io/badge/status-field%20ready-orange)
![pr](https://img.shields.io/badge/PRs-welcome-ff69b4)
![licence](https://img.shields.io/badge/licence-proprietary-red)

[Overview](#overview) · [Install](#installation) · [Usage](#usage) · [Troubleshooting](#troubleshooting) · [Glossary](#glossary)

</div>

---

## Table of contents

<details open>
<summary><b>Contents</b></summary>

1. [Overview](#overview)
2. [What Q9 is not](#what-q9-is-not)
3. [Protocol background](#protocol-background)
   - [ADB](#adb)
   - [adbd](#adbd)
   - [TCP/IP transport](#tcpip-transport)
   - [mDNS pairing](#mdns-pairing)
   - [Fastboot](#fastboot)
4. [Installation](#installation)
5. [Usage](#usage)
   - [CLI flags](#cli-flags)
   - [Menu map](#menu-map)
6. [Autonomous mode](#autonomous-mode)
7. [Automated workflows](#automated-workflows)
8. [Features and functionality](#features-and-functionality)
9. [Live camera, microphone and mirroring](#live-camera-microphone-and-mirroring)
10. [Harvest and loot](#harvest-and-loot)
11. [Monitoring and logging](#monitoring-and-logging)
12. [C2 and callback paths](#c2-and-callback-paths)
13. [CVEs, exploits and payloads](#cves-exploits-and-payloads)
14. [Device compatibility](#device-compatibility)
15. [Controls reference](#controls-reference)
16. [API reference](#api-reference)
17. [Tutorials](#tutorials)
18. [Troubleshooting](#troubleshooting)
19. [Contributing](#contributing)
20. [Glossary](#glossary)

</details>

---

## Overview

Q9 is one Python file that drives Android devices over ADB and fastboot from a
Windows host. It covers the whole arc — discovery, attachment, enumeration,
harvest, live viewing, payload staging, privilege work and cleanup — behind a
grouped menu or a single autonomous pass.

Nothing is compiled, nothing is installed. The runtime is the Python standard
library plus `colorama`; everything else is optional and probed at startup.

> **Design position.** Q9 is a driver, not a framework. It shells out to the
> platform tools that already work on your machine rather than reimplementing
> the transports. Where a step can be scripted safely it is automated; where a
> vendor build diverges, the step degrades to a warning instead of an abort.

### What Q9 is not

- Not a root exploit delivery service. `f_privesc` probes and reports; whether a
  given CVE applies depends on the build.
- Not interoperable crypto. The KEM and signature are structural, adequate for
  self-checks only.
- Not a persistent agent. There is no implant; it drives a device you have ADB
  on, or one you have just paired.

---

## Protocol background

<details>
<summary><b>ADB</b> — Android Debug Bridge</summary>

ADB is a three-part client/server/daemon model. `adb` on the host talks to a
local server, which talks to `adbd` on the device over USB or TCP. Q9 always
addresses a specific serial with `-s` so a second attached device can never
absorb a command meant for the first.

Discovery uses `adb devices -l`, which lists serials, transport and model.
</details>

<details>
<summary><b>adbd</b> — the device daemon</summary>

`adbd` is what actually executes `shell`, `pull` and `exec-out`. It runs as
`shell` (UID 2000) by default, which bounds what file operations can reach
without escalation. Q9's write-mode layer exists precisely to track whether a
command should be issued as `shell`, via `su`, or through `run-as`.
</details>

<details>
<summary><b>TCP/IP transport</b></summary>

`adb tcpip <port>` puts `adbd` into listening mode; `adb connect host:port`
attaches over the network. Default is 5555. Q9 also probes 5556, 5585 and 5557
because vendors and prior sessions move it.

The exposure this creates is the reason the /24 sweep exists: anything
listening on those ports with debugging authorised is attachable.
</details>

<details>
<summary><b>mDNS pairing</b></summary>

Android 11+ supports wireless debugging with a pairing code, advertised over
mDNS as `_adb-tls-pairing._tcp`. `adb pair host:port code` completes the
handshake, after which the device appears in `adb devices` without a cable.
`f_pair` and `f_pair_qr` implement the manual and QR paths; `f_mdns` enumerates
advertised records.
</details>

<details>
<summary><b>Fastboot</b></summary>

A separate, lower-level protocol on the bootloader. Partitions, `vbmeta`, slot
selection and OEM commands are reachable here that ADB cannot touch. Q9
resolves `fastboot` independently and warns if it is absent, since bootloader
work is impossible without it.
</details>

---

## Installation

**Requirements:** Python 3.8+, Windows 10/11, `adb` and `fastboot` from
platform-tools.

```bat
git clone <repo>
cd <repo>
pip install colorama
python Q9.py --doctor
```

`--doctor` reports python version, pip, package managers, disk, adb, fastboot,
server state, optional modules and local IP. Aim for a full pass before use.

If `adb` is missing, Q9 offers to download platform-tools into a local
directory and use it from there.

**Optional modules**, probed and used when present: `qrcode`, `PIL`,
`llama_cpp`, `scrcpy`.

---

## Usage

```bat
python Q9.py                  :: interactive menu
python Q9.py --selftest       :: ten self-checks, no device required
python Q9.py --doctor         :: environment report
python Q9.py --auto           :: autonomous pass, no prompts
```

### CLI flags

| Flag | Effect |
|---|---|
| `--selftest` | run the ten built-in checks and exit |
| `--doctor` | environment report |
| `--auto` | autonomous discovery, attach and harvest |
| `--write-mode=root\|shell\|auto` | preselect the write path |

### Menu map

| # | Group | Action |
|---|---|---|
| 1 | Autonomous | Autonomous run |
| 2 | Connect | Install / repair tooling |
| 3 | Connect | Scan network |
| 4 | Connect | Connect by ip:port |
| 5 | Connect | List devices |
| 6 | Connect | Wireless ADB |
| 7 | Connect | Fastboot |
| 8 | Recon | Fingerprint |
| 9 | Recon | ADB shell |
| 10 | Recon | Wi-Fi extras |
| 11 | Recon | Script |
| 12 | Live view & media | Live camera |
| 13 | Live view & media | Capture photo |
| 14 | Live view & media | Microphone |
| 15 | Live view & media | Mirror |
| 16 | Live view & media | Stream |
| 17 | Delivery | Callback writer |
| 18 | Delivery | WASM stage |
| 19 | Delivery | Kernel module |
| 20 | Cleanup | Wipe traces |
| 21 | System | Write mode |
| 22 | System | Self-test |
| 23 | View | View loot |
| 24 | View | View event log |

Host IP is printed under the logo and on every redraw.

---

## Autonomous mode

Option 1, or `--auto`. No prompts at any point.

1. Resolve `adb`; abort quietly if absent.
2. Derive the host /24 from the live address.
3. Enumerate `adb devices`, mDNS records and the /24 on the alternate ports.
4. Attach to every candidate, recording failures.
5. For each attached device, harvest into its own loot directory.
6. Log every step; return a device and artefact count.

Every stage is wrapped, so one unresponsive host or one denied provider does
not stop the pass. The subnet comes from the host address — you never type it.

---

## Automated workflows

<details>
<summary><b>Discovery</b></summary>

`adb devices -l`, `adb mdns services`, and a TCP sweep of 5555/5556/5585/5557
across the local /24. Results are deduplicated before attachment.
</details>

<details>
<summary><b>Attachment</b></summary>

`adb connect` for network candidates, `adb get-state` to confirm. A candidate
that never reports `device` is dropped from the run.
</details>

<details>
<summary><b>Fingerprint</b></summary>

`getprop` over model, manufacturer, release, SDK, patch level, build id and
ABI, plus a `which su` probe. Drives CVE applicability in the scanner.
</details>

<details>
<summary><b>Harvest</b></summary>

Eight collectors: contacts, SMS, call log, third-party packages, Wi-Fi, fused
location, all properties, account records, plus a DCIM index. Each writes a
separate file and logs success or emptiness.
</details>

<details>
<summary><b>Staging and cleanup</b></summary>

Payloads stage to a temporary device path, get pulled or executed, then the
remote copy is removed. `Wipe traces` clears logcat, staged files, carrier
config and the probe setting.
</details>

---

## Features and functionality

| Area | Capability |
|---|---|
| Discovery | USB, TCP/IP, mDNS, /24 sweep |
| Attachment | serial-pinned connect, reconnect, forget |
| Enumeration | fingerprint, packages, battery, identity, properties |
| Shell | interactive shell, one-shot exec |
| File ops | pull, push, ls, delete, APK extract |
| Input | tap, swipe, type, keyevent, unlock, lock |
| Harvest | contacts, SMS, calls, calendar, WhatsApp, screenshots, camera roll |
| Live | camera view, photo capture, mic capture, mirror, stream |
| Delivery | callback writer, WASM stage, MP4 polyglot, GIF polyglot, embedded carrier |
| Escalation | privesc probe, FRP, Play Protect state, write-mode selection |
| Network | reverse shell, pair, pair by QR, mDNS |
| Fastboot | devices, getvar, unlock, flash boot, vbmeta, slots, OEM, erase |
| Kernel | module staging |
| Cleanup | wipe traces |
| Ops | autonomous run, loot browser, event log, self-test, doctor |

---

## Live camera, microphone and mirroring

All three share the ADB transport used by mirroring.

**Live camera** — launches `STILL_IMAGE_CAMERA`, pulls `exec-out screencap`
frames into `live.png`, opens the file once and refreshes it in place. Front
lens selection uses `KEYCODE_SWITCH_CHARACTER`. ENTER stops the loop.

**Capture photo** — same launch, `KEYCODE_CAMERA` to trigger the shutter, waits
for the write, then pulls the newest file from `/sdcard/DCIM/Camera`.

**Microphone** — `screenrecord` for a chosen duration, pulled to loot. Where the
build exposes an audio source the track is included; otherwise capture is
video-only and the script says so. Ceiling is `screenrecord`'s 30 minutes.

**Mirror / stream** — `scrcpy` when present, raw stream otherwise.

> Vendor builds that open a gallery instead of a camera app will show the
> gallery. Check the frame content before assuming the lens failed.

---

## Harvest and loot

```
~/.pegasus/loot/<serial>_<YYYYmmdd_HHMMSS>/
    contacts.txt  sms.txt  calls.txt  apps.txt
    wifi.txt  location.txt  props.txt  accounts.txt
    dcim_index.txt
```

One directory per device per run, timestamped. *View loot* lists the twenty most
recent with file counts.

---

## Monitoring and logging

Every automated step appends to `~/.pegasus/events.log`:

```
2026-11-04 11:52:07 [auto] start 10.1.10
2026-11-04 11:52:19 [harvest] 10.1.10.44:5555 contacts ok
2026-11-04 11:52:31 [auto] done 1/9
```

*View event log* tails the last sixty lines. The log is append-only and never
rotated automatically; truncate it yourself if it grows.

---

## C2 and callback paths

<details>
<summary><b>Callback writer</b></summary>

Generates a minimal callback artefact bound to a host and port, staged for
delivery. Suitable as a first-stage beacon when a full agent is unnecessary.
</details>

<details>
<summary><b>Reverse shell</b></summary>

Device-initiated shell back to the host over TCP, for NAT-bound targets where
inbound attach is impossible.
</details>

<details>
<summary><b>Relay and beacon</b></summary>

Beacon registrations land on the relay route set; sessions are tracked by
serial so a reconnecting device resumes rather than duplicating.
</details>

<details>
<summary><b>Transport choices</b></summary>

USB where physical access exists, TCP/IP where the port is reachable, mDNS
pairing where the device is on the same segment and the user can read a code.
</details>

---

## CVEs, exploits and payloads

Q9 stages carriers rather than shipping a PoC per CVE. The families exercised:

| Identifier | Component | Class |
|---|---|---|
| CVE-2024-0044 | `run-as` / package manager | privilege escalation |
| CVE-2023-35674 | task hijacking | activity hijack |
| CVE-2022-20465 | SIM PIN / lockscreen | lock bypass |
| CVE-2021-39698 | kernel | use-after-free |
| CVE-2020-0423 | binder | use-after-free |

**Carrier formats:**

- **WASM** — a hand-built module validated section by section, including a
  truncation negative case.
- **MP4 polyglot** — valid MP4 with appended payload, `ftyp` preserved.
- **GIF polyglot** — valid GIF with trailing carrier.
- **Embedded** — payload appended to a host file with an offset record.
- **Kernel module** — staged `.ko` pushed and loaded where write mode allows.

`--selftest` validates every builder against a deliberate truncation, so a
malformed header is caught before a device ever sees it.

---

## Device compatibility

| Requirement | Detail |
|---|---|
| Android | 5.0–15 |
| USB debugging | must be authorised |
| Wireless | 11+ for pairing; `tcpip` for any version |
| Fastboot | unlocked bootloader for flash and erase |
| Root | not required; expands what write mode can reach |

**Known friction:** MIUI and HyperOS require "USB debugging (Security
settings)"; Samsung needs a re-authorise after each reboot; some OEM builds
bind `adbd` to loopback so a network sweep finds nothing until `tcpip` runs.

---

## Controls reference

| Key | Context | Effect |
|---|---|---|
| `1`–`24` | menu | run action |
| `0` | menu | quit |
| ENTER | live camera | stop capture |
| `y`/`n` | prompts | default is shown in capitals |
| `root`/`shell`/`auto` | write mode | select write path |
| Ctrl-C | anywhere | abort current action, not the app |

---

## API reference

Internal callables, for extension work.

<details>
<summary><b>Transport</b></summary>

| Function | Signature | Notes |
|---|---|---|
| `shell` | `(cmd, timeout=...)` | returns `(rc, stdout, stderr)` |
| `run` | `(argv, timeout=...)` | list form, no shell |
| `need` | `()` | guards a device-dependent action |
</details>

<details>
<summary><b>Discovery and attachment</b></summary>

| Function | Notes |
|---|---|
| `adb_inventory()` | devices + mDNS, deduplicated |
| `_subnet_scan(base)` | TCP sweep of the alternate ports |
| `_try_access(serial)` | connect then `get-state` |
| `local_base()` | /24 from the host address |
</details>

<details>
<summary><b>Harvest and state</b></summary>

| Function | Notes |
|---|---|
| `harvest(serial, dest)` | eight collectors, returns count |
| `loot_dir(serial)` | creates a timestamped directory |
| `event(kind, msg)` | appends to the event log |
</details>

<details>
<summary><b>Builders</b></summary>

| Function | Validator |
|---|---|
| `build_wasm()` | `validate_wasm` |
| `build_mp4()` | `validate_mp4` |
| `build_gif()` | `validate_gif` |
</details>

---

## Tutorials

<details>
<summary><b>First attach over USB</b></summary>

1. Enable developer options, then USB debugging.
2. Connect; accept the RSA prompt on the device.
3. `python Q9.py --doctor` — adb and devices should be green.
4. Menu → `List devices`, confirm your serial, then `Fingerprint`.
</details>

<details>
<summary><b>Go wireless</b></summary>

1. Attach over USB first and authorise.
2. Menu → `Wireless ADB`, note the port it prints.
3. Unplug, then `Connect by ip:port` with `host:port`.
4. `List devices` should show it over TCP.
</details>

<details>
<summary><b>Pair with a code (Android 11+)</b></summary>

1. Developer options → Wireless debugging → Pair device with pairing code.
2. Menu → `Pair`, enter `host:port` and the six digits.
3. `List devices`, then `Connect by ip:port` on the debug port.
</details>

<details>
<summary><b>Autonomous sweep</b></summary>

1. Confirm the host is on the same segment as the targets.
2. `python Q9.py --auto`.
3. Watch the event log; then `View loot`.
</details>

<details>
<summary><b>Watch the rear camera</b></summary>

1. Attach and unlock the device.
2. Menu → `Live camera`, answer `n` for rear.
3. `live.png` opens; frames refresh in place. ENTER stops.
</details>

---

## Troubleshooting

<details>
<summary><b>`adb: no devices/emulators found`</summary>

Cable or authorisation. Reconnect, check for the RSA prompt, then
`List devices`. On Windows install the OEM USB driver — the generic one leaves
the device in `unauthorized`.
</details>

<details>
<summary><b>`getaddrinfo failed` on scan</b></summary>

The base is malformed. Q9 strips `/24` and a trailing `.0`, but a base like
`10.1.10.5` becomes `10.1.10.5.1`. Enter `10.1.10` or `10.1.10.0/24`.
</details>

<details>
<summary><b>Scan finds nothing but the device is on Wi-Fi</b></summary>

`adbd` is bound to loopback. Attach over USB and run `Wireless ADB` once to put
it on the network.
</details>

<details>
<summary><b>Camera shows the gallery</b></summary>

The OEM build does not honour `STILL_IMAGE_CAMERA`. Open the camera app by hand
first, then run `Live camera`.
</details>

<details>
<summary><b>Microphone file has no sound</b></summary>

The build's `screenrecord` lacks an audio source. The script prints
`(video only)` when it detects this. Use a build with an audio-capable
`screenrecord`, or capture on the device.
</details>

<details>
<summary><b>`NameError` on a menu row</b></summary>

An action references a function that does not exist. `--selftest` exercises
menu wiring and names the gap.
</details>

<details>
<summary><b>Selftest fails on crypto</b></summary>

Expected values changed with the implementation. Check the `_sub` arity and the
`encapsulate` vector length before assuming the maths.
</details>

---

## Contributing

1. Fork, branch, keep to one concern per commit.
2. New action? Add the `f_` function, register it in `ACTIONS`, add a label,
   and place it in the right `MENU_GROUPS` entry.
3. `python -m py_compile Q9.py` and `--selftest` must both be clean before a PR.
4. Keep the runtime to the standard library; anything else is probed.
5. Document new failure modes in Troubleshooting, not in code comments alone.

Style: type hints on signatures, `note`/`ok`/`warn`/`err` for output, no bare
`print` in new code.

---

## Glossary

<details>
<summary><b>Terms</b></summary>

| Term | Meaning |
|---|---|
| **ADB** | Android Debug Bridge — host client, local server, device daemon |
| **adbd** | the on-device daemon ADB commands reach |
| **fastboot** | bootloader-level protocol, separate from ADB |
| **serial** | unique device identifier used with `-s` |
| **transport** | how a device is attached — USB or TCP |
| **tcpip mode** | `adbd` listening on a port for network attach |
| **mDNS** | multicast DNS; carries the pairing advertisement |
| **pairing code** | six digits authorising a wireless attach |
| **write mode** | `root`, `shell` or `auto` — how privileged commands are issued |
| **`su`** | superuser binary; presence gates root write mode |
| **run-as** | execute as an app's UID; basis of one escalation path |
| **FRP** | Factory Reset Protection |
| **vbmeta** | verified-boot metadata partition |
| **slot** | A/B partition set indicator |
| **polyglot** | file valid in two formats at once |
| **carrier** | payload host file |
| **loot** | harvested artefacts under `~/.pegasus/loot` |
| **event log** | append-only record of automated steps |
| **KEM** | key encapsulation mechanism |
| **negacyclic** | convolution mod `xⁿ+1`, as Kyber requires |
| **self-test** | ten built-in checks, device-free |

</details>

---

<div align="center">

**Q9** — drive the device you have, not the one the datasheet promised.

[Back to top](#q9--pegasus-pro)

</div>
