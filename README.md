# GrainBernik

[English](README.md) | [Русский](README_RU.md)

**GrainBernik** is an unofficial add-on for the granular ambient instrument
[GrainBrick](https://github.com/ETRNLIAM/GrainBrick) by ETRNLIAM, made for the
**Anbernic RG40XX H** running the official **ROCKNIX**.

It does **not** modify or redistribute GrainBrick: the closed application is taken
from your own copy of the official ZIP, and GrainBernik only adds launchers,
adapters and a USB audio stack on top of it.

| You run | Use GrainBernik | Guide |
|---|---|---|
| GrainBrick **BETA 2.0** (RHYTHM, ORBIX Rings, OSCILLATOR, LIVE, GRAIN 2/3) | **v0.3.x** (this page) | below |
| GrainBrick beta **1.0.1** | v0.2.x | [docs/LEGACY_1_0_1.md](docs/LEGACY_1_0_1.md) |

## What GrainBernik 0.3 adds to GrainBrick BETA 2.0

- **The RG40XX H as a two-way USB sound card for an iPhone.** GrainBrick plays
  to the console headphones *and* the iPhone at once, and records or processes
  the iPhone sound (SAMPLE → record, LIVE → USB input). External USB audio
  devices (e.g. M-VAVE FM1, Zoom H1n) keep working.
- **STICKS & BUTTONS.** Both sticks (X/Y), L2/R2 and the stick clicks L3/R3 become
  independent sound controls: 61 parameters for the sticks, 29 button effects,
  11 presets and one User slot — including **RHYTHM**, **ORBIX Rings**,
  **OSCILLATOR**, **LIVE** and **GRAIN 2/3**.
- **Native feel.** Both pages follow the BETA 2.0 *Console Controls*
  (A enters / edits, B goes back, LEFT/RIGHT edit, **hold A + LEFT/RIGHT** =
  quick edit) and are available in English and Russian (INFO language).
- **ROCKNIX launcher.** Separate Python 3.12 + pygame, performance CPU mode while
  playing, clean exit on **Select + Start**, ROCKNIX button labels (A/B, X/Y).

## Requirements

- Anbernic **RG40XX H** with the official **ROCKNIX 20261101** (DDR4 image) — see
  [the ROCKNIX note](docs/LEGACY_1_0_1.md#install-on-rocknix-recommended) for the
  SD-card preparation, Wi-Fi and SSH. The iPhone mode needs ROCKNIX (its kernel
  can run the USB sound card mode; KNULLI's cannot).
- The official **`GrainBrick_BETA_2_0.zip`** from the
  [GrainBrick releases](https://github.com/ETRNLIAM/GrainBrick/releases)
  (tag `v2.0.0-beta.2`). Do not use GitHub's "Source code" ZIP.
- A PC with Python 3 and `scp`/`ssh`. The console needs internet once (the
  installer downloads Python 3.12 and pygame, SHA-256 checked).

## Install on ROCKNIX

1. **Build the package** on the PC (Linux / WSL / macOS; on Windows run it in WSL):
   ```sh
   sh rocknix/make_package.sh /path/to/GrainBrick_BETA_2_0.zip grainbernik-rocknix
   ```
   It combines the official app with the GrainBernik adapters, the launcher and
   the prebuilt USB audio modules. (Or take the finished folder from a package
   somebody built from *their own* official ZIP — never publish the official files.)
2. **Copy and install** (default password `rocknix`):
   ```sh
   scp -r grainbernik-rocknix root@<console-ip>:/storage/
   ssh root@<console-ip> "sh /storage/grainbernik-rocknix/install.sh"
   ```
3. **Restart the menu:** `ssh root@<console-ip> systemctl restart essway`
   (or Start → Quit → Restart EmulationStation). **GrainBrick BETA 2.0** appears in
   **PORTS**.

Installed locations: the app in `/storage/roms/ports/grainbrick-beta2/`, the
launcher `GrainBrick BETA 2.0.sh` next to it, Python in
`/storage/grainbrick-python`, USB audio files in `/storage/uac2`. The 1.0.1
installation (`grainbrick beta 1.0.1/`) is not touched and can stay side by side.

**Updating** — build a new package and run `install.sh` again. Your `samples`,
`projects`, `recordings`, `settings.json` (it also holds STICKS & BUTTONS),
`gb_usb_audio.json` and the other state files are kept. First install from 1.0.1:
`gb_usb_audio.json` is migrated; copy your samples and projects by hand if you
want them in BETA 2.0.

**Removing** — delete `/storage/roms/ports/grainbrick-beta2/` and
`/storage/roms/ports/GrainBrick BETA 2.0.sh` (back up samples/projects first);
`/storage/uac2` and `/storage/grainbrick-python` can go as well.

## Controls (BETA 2.0 "Console Controls")

| Action | Buttons |
|---|---|
| Enter a menu / start editing a field | **A** |
| Leave / stop editing | **B** |
| Change the value while editing | **LEFT / RIGHT** |
| Quick change without entering edit mode | hold **A**, press **LEFT/RIGHT**, release **A** |
| Switch main tabs | **L1 / R1** |
| Exit GrainBrick | **Select + Start** |

On ROCKNIX the launcher swaps A/B and X/Y for GrainBrick so the labels match the
console's printed buttons.

## IPHONE / USB AUDIO

**SETTINGS →** scroll to **IPHONE / USB AUDIO** → **A**.

| Row | Meaning |
|---|---|
| MODE | **OFF** · **USB INTERFACE** (an external USB sound card) · **IPHONE** (the console is a USB sound card for the iPhone) |
| SEND TO IPHONE | GrainBrick plays to the headphones/speaker **and** the iPhone |
| RECORD FROM IPHONE | use the iPhone sound as USB input for recording and LIVE |
| STATUS | `CONNECT IPHONE` / `IPHONE CONNECTED` / `PRESS A` (restart the gadget) |

1. Choose **MODE → IPHONE** (USB sound card mode starts by itself, no SSH).
2. Connect the iPhone to the console's USB-C OTG port with a USB-C cable. The
   status changes to **IPHONE CONNECTED**.
3. **Console → iPhone:** in an iPhone app (Voice Memos, GarageBand, a camera app)
   select the console as the audio input.
4. **iPhone → console:** play audio on the iPhone; in GrainBrick use
   **SAMPLE → record** or **LIVE** and choose the **USB** input. Monitoring is
   the native one of BETA 2.0 (REC screen).
5. **MODE → OFF** returns the normal ROCKNIX USB mode.

*External USB devices (FM1, Zoom H1n):* leave the mode on **OFF** or **USB
INTERFACE**, plug the device in; it is detected like in the stock app.

iOS may show *"Accessory uses too much power"* because the console is powered
over the cable. Audio still works; a USB-C hub with PD pass-through charging
removes the warning. Technical details (UAC2 gadget, PipeWire `gb_both` output,
why ROCKNIX): [docs/USB_AUDIO.md](docs/USB_AUDIO.md).

## STICKS & BUTTONS

**SETTINGS →** the last row, **STICKS & BUTTONS** → **A**. The row shows the
active preset (`NONE`, a preset name, or `USER`) and its description explains
the item under the cursor. Everything is **OFF** by default.

**Main page:** Left Stick · Right Stick · L2 Button · R2 Button · L3 Click ·
R3 Click · Preset · Reset to Defaults · Back.

- **Sticks:** *Enabled*, *X Effect*, *Y Effect* (61 parameters, see below) and
  *Stick Options*: deadzone, sensitivity, invert X/Y, **Spring** (returns to
  the start value) or **Latch** (keeps the value), smoothing, physical axes.
- **L2 / R2 / L3 / R3:** *Enabled*, *Effect*, *Mode* — **Hold** (while pressed) or
  **Toggle** (press on / press off). L3/R3 default to Toggle; the *Step* effects
  change the value once per press and keep it.
- **Preset:** pick a preset → confirm with **A**. *Save User* / *Load User* keep
  one personal setup. Presets change only assignments, never the sound itself.
  **If you change any assignment, the active preset becomes `USER`.**

**What can be assigned**

| Group | Stick parameters (examples) |
|---|---|
| GRAIN, GRAIN 2/3 | position, size, density, pitch, spray, pitch spread, size/timing random, reverse chance, envelope; roam speed/range/wander |
| FX, TAPE | delay time/feedback/mix/lowpass, reverb mix/size/decay/damp, shimmer mix/pitch/feedback, tape saturation/wow/flutter/hiss |
| ORBIX | gravity, rotation, bounce, volume, attack, release, reverb, balls, root, scale, instrument, octave, shape |
| **ORBIX Rings** | structure, brightness, damping, position, mix, tune, detune, stereo, noise, excite mix |
| **OSCILLATOR** | blend, dry/wet, drive, X-mod, A/B balance, level |
| **RHYTHM / LIVE** | tempo BPM and offset, input level, master level |

| Button effect | What it does |
|---|---|
| Freeze, Reverse, Stutter | native Motion hold / reverse / jump+chaos |
| Delay Throw, Reverb Wash, Shimmer Burst | temporary delay / reverb / shimmer boost |
| Pitch Drop, Octave Up | ∓1 octave (relative, adds up) |
| Octave +, Octave − | **step**: every press transposes by an octave and stays |
| Grain Burst, Scatter, Reverse Grains | dense cloud / scattered pitch-size-timing / backwards grains |
| Lo-Fi, Bypass, ORBIX | tape + 8-bit / FX and EQ off / ORBIX on |
| **Rings Bloom, Rings Damp, Rings Detune** | open bright ring-out / choke the resonance / detune + wide stereo |
| **Osc On, Osc Drive, Osc FM** | oscillator on / high drive / strong cross modulation |
| **Slow Down, Speed Up** | tempo ∓20 BPM while held; the old tempo returns |
| **Tempo +5, Tempo −5** | **step**: tempo ±5 BPM per press |
| **Input Cut, Input Boost, Mute Out** | LIVE input to minimum / +6 dB / master mute while held |

**Presets** (left stick X/Y · right stick X/Y · L2 · R2 · L3 · R3):

| Preset | Left | Right | L2 | R2 | L3 | R3 |
|---|---|---|---|---|---|---|
| Granular | Position / Size | Pitch / Density | Freeze | Reverse | Octave − | Octave + |
| Ambient | Position / Spray | Reverb / Shimmer | Freeze | Reverb Wash | Shimmer Burst | Bypass |
| Texture | Size / Spray | Density / Roam Speed | Grain Burst | Freeze | Reverse | Stutter |
| Echo | Delay Time / Feedback | Delay Mix / Reverb Mix | Delay Throw | Reverb Wash | Freeze | Bypass |
| Tape | Saturation / Wow | Pitch / Flutter | Pitch Drop | Lo-Fi | Reverse | Bypass |
| ORBIX Play | Rotation / Gravity | Bounce / Reverb | ORBIX | Reverb Wash | Freeze | Shimmer Burst |
| **Rhythm** | Position / Size | Density / Pitch | Slow Down | Speed Up | Tempo −5 | Tempo +5 |
| **Rings** | Structure / Brightness | Damping / Position | Rings Bloom | Rings Damp | ORBIX | Rings Detune |
| **Oscillator** | Blend / Drive | X-Mod / Dry-Wet | Osc FM | Osc Drive | Osc On | Bypass |
| **Live** | Position / Input Level | Density / Spray | Input Cut | Mute Out | Freeze | Grain Burst |
| **Grain 2/3** | Size Random / Timing Random | Pitch Spread / Reverse Chance | Scatter | Reverse Grains | Freeze | Octave + |

**Good to know**

- The controls act on **GRAIN, FX, TAPE and VISUAL**; L2/R2 are left to the app on
  other screens. While L3/R3 are **ON** the stick clicks do not switch tabs.
  Toggle effects stay on across tabs; they end when toggled again, when the page
  is opened, or on exit.
- When two effects change the same parameter, the one pressed last wins; the
  relative ones (Octave Up, Pitch Drop, Slow/Speed Up, Input Boost) add up.
- RHYTHM pattern parameters live inside the RHYTHM engine, not in the parameter
  list, so only the shared **tempo** is assignable. A Hold on tempo fights LINK
  and tap tempo while pressed.
- Settings are stored in `settings.json` (`grainbernik_advanced`); assignments
  from the 1.0.1 version load too (parameters that no longer exist become *None*).
- Full reference: [docs/STICKS_AND_BUTTONS.md](docs/STICKS_AND_BUTTONS.md).

## Not in 0.3 yet

- The shorter SETTINGS menu (AUDIO / CONTROLS) and **deleting recordings from
  inside SAMPLE** of the 1.0.1 line — planned (step "2b" in
  [docs/BETA2_PORT.md](docs/BETA2_PORT.md)).
- Not measured on the H700 yet: the CPU load of the **Rings** resonator and of
  **LIVE** at high settings; **Bluetooth MIDI** on ROCKNIX; using an iPhone
  and a USB MIDI host on the single OTG port at the same time.
- KNULLI is not supported by the BETA 2.0 launcher (the iPhone mode cannot work
  there anyway); the stock KNULLI instructions of the author apply.

## Troubleshooting

| Problem | What to do |
|---|---|
| GrainBrick BETA 2.0 is not in PORTS | `systemctl restart essway`; check `/storage/roms/ports/GrainBrick BETA 2.0.sh` |
| Black screen / back to menu | read `/storage/roms/ports/grainbrick-beta2/gb_launch.log` (lines `GRAINBERNIK ADAPTER FAILED` / `GB ADVANCED` / `GB USB AUDIO`) |
| STICKS & BUTTONS or IPHONE row is missing | the adapter did not load: see the log; `GRAINBERNIK_ADVANCED=0` / `GRAINBERNIK_USB_AUDIO=0` switch them off |
| Status stays `CONNECT IPHONE` | use a data-capable USB-C cable in the OTG port, press **A** on the STATUS row, then reconnect |
| No sound | check the AUDIO OUTPUT and OUTPUT BOOST rows in SETTINGS and the iPhone page's MODE |
| Diagnostics | `sh /storage/grainbernik-rocknix/gb-diag.sh` |

## Options

Add `export NAME=value` lines to `GrainBrick BETA 2.0.sh` before the Python line.

| Variable | Values | Meaning |
|---|---|---|
| `GRAINBERNIK_ADVANCED` | `0` | Disable STICKS & BUTTONS |
| `GRAINBERNIK_USB_AUDIO` | `0` | Disable the iPhone / USB audio adapter |
| `GRAINBERNIK_SWAP_ABXY` | `1` / `0` | Swap A/B and X/Y for GrainBrick (default 1) |
| `GRAINBRICK_DISPLAY_FILTER` | `smooth` / `fast` | Native display scaling (default `smooth`) |

Tests: `GRAINBRICK_BETA2_ZIP=/path/to/GrainBrick_BETA_2_0.zip python3 -m pytest tests`
(native ARM64 tests are skipped on other machines).

## Building the USB audio modules

Prebuilt `u_audio.ko` and `usb_f_uac2.ko` for ROCKNIX 20261101 (kernel 7.2.0) are in
[`rocknix/uac2/`](rocknix/uac2/); how they were built and how to rebuild them:
[docs/LEGACY_1_0_1.md](docs/LEGACY_1_0_1.md#building-the-usb-audio-modules).

## Licensing

This repository contains only GrainBernik's own files and no GrainBrick code.
GrainBrick is free to download but **not open source**; its notices and
third-party licenses (SoundTouch, Mutable Instruments Rings, NumPy) are in the
official package. Do not redistribute the official files.
