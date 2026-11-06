# GrainBernik

[English](README.md) | [Русский](README_RU.md)

**GrainBernik** is an unofficial patch of [ETRNLIAM/GrainBrick](https://github.com/ETRNLIAM/GrainBrick)
(granular ambient instrument) for the **Anbernic RG40XX H** (640×480).

Highlights:

- **The RG40XX H as a two-way USB sound card for iPhone** (ROCKNIX): GrainBrick
  plays to the console headphones **and** the iPhone at the same time, records
  the iPhone sound into SAMPLE, with input monitoring — similar to using an
  Akai MPC Sample with an iPhone.
- **Sticks & Buttons**: left/right stick X/Y, L2/R2 and the stick clicks L3/R3
  as independent sound controls, with 6 presets.
- **Delete recordings** directly in the SAMPLE browser.
- RG40XX H button layout and labels.

The patch does not modify or redistribute the closed GrainBrick application:
you need the official `grainbrick.beta.1.0.1.zip` from the original author.

**Download:** [GrainBernik v0.2.0-beta.1](https://github.com/AlekseyMalykh/GrainBernik/releases/tag/v0.2.0-beta.1)
— **patch** ZIP for a fresh install, **update** ZIP for an existing one
([release notes](docs/releases/v0.2.0-beta.1.md)).

> **Status (2026-11-06):** tested on an RG40XX H with the **official ROCKNIX
> 20261101 (DDR4 image)** and an **iPhone 16**: playback to headphones + iPhone,
> recording from the iPhone, monitoring, L3/R3, presets and recording deletion
> work. KNULLI keeps working as before, but its kernel cannot run the USB sound
> card mode (see [Why ROCKNIX](#why-rocknix-for-iphone)).

## Contents

- [Install on ROCKNIX (recommended)](#install-on-rocknix-recommended)
- [Settings menu](#settings-menu)
- [iPhone / USB audio](#iphone--usb-audio)
- [Deleting recordings](#deleting-recordings)
- [Sticks & Buttons](#sticks--buttons)
- [Buttons](#buttons)
- [Install on KNULLI](#install-on-knulli)
- [Building the USB audio modules](#building-the-usb-audio-modules)
- [Options](#options)

## Install on ROCKNIX (recommended)

1. **ROCKNIX:** write the official `ROCKNIX-H700.aarch64-20261101-DDR4.img.gz`
   ([releases](https://github.com/ROCKNIX/distribution/releases)) with Raspberry
   Pi Imager. On the **ROCKNIX** partition copy
   `device_trees/sun50i-h700-anbernic-rg40xx-h.dtb` to the root and rename the
   copy to `dtb.img`. (On our RG40XX H the DDR3 image does not boot.)
   Connect Wi-Fi and enable SSH in the ROCKNIX menu.
2. **Package:** on a PC with Python 3 (Linux/WSL/macOS):
   ```sh
   sh rocknix/make_package.sh /path/to/grainbrick.beta.1.0.1.zip grainbernik-rocknix
   ```
   It combines the official app, the GrainBernik patch, the ROCKNIX launcher
   and the prebuilt USB audio modules.
3. **Copy and install** (password `rocknix`):
   ```sh
   scp -r grainbernik-rocknix root@<console-ip>:/storage/
   ssh root@<console-ip> sh /storage/grainbernik-rocknix/install.sh
   ```
   The installer downloads Python 3.12 (python-build-standalone) and pygame
   2.6.1 once into `/storage/grainbrick-python` (SHA-256 checked), uses the
   ROCKNIX SDL2, copies GrainBrick to `/storage/roms/ports` and the USB audio
   files to `/storage/uac2`. ROCKNIX system files are not modified.
4. Restart the menu (`systemctl restart essway`) — **GrainBrick beta 1.0.1**
   appears in **PORTS**. To update later, rebuild the package, copy it and run
   `install.sh` again; your samples, projects and settings stay.

The ROCKNIX launcher runs the CPU in `performance` mode while GrainBrick is open
and disables the unused pygame mixer (`SDL_AUDIODRIVER=dummy`), which fixes the
exit hang on **Select + Start**; a stalled audio worker is cleaned up on exit.

**Updating** an existing installation: extract the **update** ZIP, copy
`grainbrick-beta/*` into `/storage/roms/ports/grainbrick beta 1.0.1/` and
`rocknix/GrainBrick beta 1.0.1.sh` into `/storage/roms/ports/` (both are
needed). Settings, samples, projects and recordings are kept.

## Settings menu

**SETTINGS** is reduced to five entries; the native items moved to OTHER:

| Entry | Contents |
|---|---|
| **AUDIO** | Quick page: **CONNECTION** (AUTO / IPHONE), **INPUT** (detected USB input), **OUTPUT** |
| **AUDIO / ADVANCED** | The full IPHONE / USB AUDIO page below, plus PLAYBACK OUTPUT |
| **CONTROLS** | Presets of Sticks & Buttons (opens the preset list directly) |
| **CONTROLS / ADVANCED** | Full Sticks & Buttons editor |
| **OTHER SETTINGS** | Info language, save on exit, button mapping, reset sound |

USB audio devices (e.g. an FM1 or Zoom H1n) are detected when plugged in while
the app runs. Lists wrap around at both ends. In editors **A** increases and
**B** decreases a value; on navigation rows **B** goes back.

## iPhone / USB audio

**SETTINGS → AUDIO / ADVANCED** (page *IPHONE / USB AUDIO*):

| Item | Meaning |
|---|---|
| MODE | **OFF** · **USB INTERFACE** (external USB sound card, e.g. Zoom H1n) · **IPHONE** (the console is a USB sound card for the iPhone) |
| SEND TO IPHONE | GrainBrick plays to the headphones/speaker **and** the iPhone |
| RECORD FROM IPHONE | record the iPhone sound in SAMPLE |
| MONITOR WHILE RECORDING | hear the iPhone in the headphones while recording |
| STATUS | `CONNECT IPHONE (USB-C)` / `IPHONE CONNECTED` / `NOT STARTED - PRESS A` |
| PLAYBACK OUTPUT | GrainBrick's own output selection |

Choosing **IPHONE** starts the USB sound card mode by itself (no SSH needed);
**OFF** returns the normal ROCKNIX USB mode.

1. Connect the iPhone to the console's USB-C OTG port (USB-C ↔ USB-C).
2. **Console → iPhone:** in an iPhone app (Voice Memos, GarageBand…) the input
   becomes the console; GrainBrick plays to the headphones and the iPhone.
3. **iPhone → console:** play sound on the iPhone; in GrainBrick open
   **SAMPLE → Y RECORD → USB AUDIO** and press **A**.
4. **Monitoring:** while recording from the iPhone its sound is heard in the
   console headphones (never sent back to the iPhone). **SELECT during
   recording** turns monitoring on/off; the choice is remembered.
5. With headphones plugged in, the speaker is muted (ROCKNIX does not do this
   by itself on this console).
6. After the iPhone is unplugged, GrainBrick's INTERNAL output always returns
   to the console (a stale system default on the USB card is repaired).
7. A recording interrupted by unplugging is finalized (WAV header repaired)
   before the editor opens, so saving it no longer runs out of memory.

iOS shows *"Accessory uses too much power"*: the console charger draws power
from the iPhone (limited to the 100 mA minimum in this mode). Audio still
works, but iOS may drop the connection. A **USB-C hub with PD pass-through
charging** between the iPhone and the console removes the warning.

Technical details: stereo 16-bit 48 kHz in both directions (Linux `f_uac2`).
Routing is done by PipeWire: a combined output `gb_both` (headphones + iPhone,
clock-compensated), recording from the gadget source, monitoring via
`pw-loopback`. Do not stop PipeWire — on ROCKNIX it is also the built-in sound.

### Why ROCKNIX for iPhone

The KNULLI kernel (Allwinner BSP 4.9) fails to bind the UAC2 function
(`afunc_bind`: no isochronous IN endpoint). ROCKNIX uses mainline Linux 7.2
with the MUSB driver, whose device mode works. Its kernel has no UAC2 built
in, so GrainBernik loads two out-of-tree modules (`rocknix/uac2/`). History of
the failed custom-image attempt: [`tools/legacy-rocknix-test-image/`](tools/legacy-rocknix-test-image/).

## Deleting recordings

In **SAMPLE**, open the **RECORDINGS** folder and select a recording. The hint
`SELECT: DELETE RECORDING` appears. Press **SELECT**, then **SELECT again**
within 4 s (`SELECT AGAIN: DELETE <name>`). Only WAV files in
`samples/recordings` can be deleted; the **loaded** (playing) sample is
protected; demo samples and other folders are never touched — there SELECT
keeps its native INFO function.

## Sticks & Buttons

**SETTINGS → CONTROLS / ADVANCED** (formerly Advanced Settings; presets also via **CONTROLS**): six independent
controls, all **OFF** by default — **Left Stick**, **Right Stick** (X/Y
parameters), **L2**, **R2**, **L3 Click**, **R3 Click** (effects).

- **Sticks:** any of 31 engine parameters per axis, deadzone, sensitivity,
  inversion, Spring/Latch, smoothing, physical axis.
- **Button effects:** Freeze, Reverse, Delay Throw, Reverb Wash, Pitch Drop,
  Octave Up, Shimmer Burst, Grain Burst, Lo-Fi, Stutter, Bypass, ORBIX, and the
  step actions **Octave +** / **Octave −**.
- **Modes:** **Hold** (while pressed), **Toggle** (press on / press off — the
  default for L3/R3), **Step** (Octave ±: every press transposes the grains by
  one octave and keeps it, limited to ±24).
- Toggle effects stay on when switching tabs; they are released by pressing
  again, opening this menu or exiting. Hold effects and sticks are released
  outside the sound tabs.
- When effects change the same parameter, the most recent one wins; Pitch
  Drop/Octave Up are relative and add up.
- While L3/R3 are **ON**, stick clicks no longer switch tabs (natively they
  are TAB−/TAB+). Effects play on GRAIN, FX, TAPE and VISUAL.

**Presets** (Presets → choose → confirm; one User slot via Save Current / Load User):

| Preset | Left X / Y | Right X / Y | L2 | R2 | L3 | R3 |
|---|---|---|---|---|---|---|
| Granular | Position / Size | Pitch / Density | Freeze | Reverse | Octave − | Octave + |
| Ambient | Position / Spray | Reverb Mix / Shimmer | Freeze | Reverb Wash | Shimmer Burst | Bypass |
| Texture | Size / Spray | Density / Roam Speed | Grain Burst | Freeze | Reverse | Stutter |
| Echo | Delay Time / Feedback | Delay Mix / Reverb Mix | Delay Throw | Reverb Wash | Freeze | Bypass |
| Tape | Saturation / Wow | Pitch / Flutter | Pitch Drop | Lo-Fi | Reverse | Bypass |
| ORBIX Play | Rotation / Gravity | Bounce / Reverb | ORBIX | Reverb Wash | Freeze | Shimmer Burst |

Presets change assignments only, not sound parameters. Settings are stored in
`settings.json` (`grainbernik_advanced`); older User slots without L3/R3 are
kept. More details: [docs/ADVANCED_SETTINGS.md](docs/ADVANCED_SETTINGS.md).

## Buttons

- **ROCKNIX:** GrainBrick 1.0.1 maps buttons itself through the SDL controller
  database (`H700 Gamepad`). ROCKNIX names face buttons by their label, while
  GrainBrick expects positional names (as on KNULLI), so the launcher swaps a/b
  and x/y for GrainBrick only. The old calibration adapter `gb_buttons` is
  **off** on ROCKNIX (it would translate twice). The native
  **SETTINGS → BUTTON MAPPING** can still rebind single buttons.
- **KNULLI:** `gb_buttons.py` records the layout on first launch
  (`gb_buttons.json`); rerun with **GrainBernik Buttons Setup** from PORTS.

## Install on KNULLI

1. Copy `grainbrick beta 1.0.1/` and `GrainBrick beta 1.0.1.sh` from the
   official ZIP to `/userdata/roms/ports/` (`roms/ports` on SHARE).
2. Copy all files from [`rg40xx-h-patch/grainbrick-beta/`](rg40xx-h-patch/grainbrick-beta/)
   into `grainbrick beta 1.0.1/` (replacing `gb_launch.py`), and
   `GrainBernik Buttons Setup.sh` from [`rg40xx-h-patch/`](rg40xx-h-patch/) to `roms/ports/`.
3. Launch from PORTS; the first launch asks for each button.

On KNULLI: external USB interfaces (e.g. Zoom H1n as *Audio Interface*) work
for output and recording; the iPhone mode does not (kernel limitation above).
The RG40XX H has no built-in microphone.

## Building the USB audio modules

Prebuilt `u_audio.ko` and `usb_f_uac2.ko` for ROCKNIX 20261101 (kernel 7.2.0)
are in [`rocknix/uac2/`](rocknix/uac2/). To rebuild (Linux/WSL with
`gcc-aarch64-linux-gnu`; the console must be reachable by SSH):

```sh
bash rocknix/build/build_uac2_modules.sh
```

It downloads Linux 7.2, applies the ROCKNIX 20261101 patches for H700, takes the
kernel config from the console, builds `vmlinux` once (10–40 min) and the two
modules. Symbol CRCs come from `rocknix/build/official.symvers`, extracted from
the official kernel with `rocknix/build/extract_kcrctab.py` (a GCC 13 build
computes different CRCs than ROCKNIX's GCC 16). For another ROCKNIX release:
copy its `/flash/KERNEL` and regenerate `official.symvers`.

Manual control on the console: `sh /storage/uac2/uac2-on.sh` /
`sh /storage/uac2/uac2-off.sh`. Diagnostics: `sh /storage/grainbernik-rocknix/gb-diag.sh`.

## Options

Environment variables (add to `GrainBrick beta 1.0.1.sh` before the Python line):

| Variable | Values | Meaning |
|---|---|---|
| `GRAINBRICK_BUTTONS` | `0` / `1` | Calibration adapter (default: on for KNULLI, off on ROCKNIX) |
| `GRAINBERNIK_SWAP_ABXY` | `1` / `0` | ROCKNIX: swap a/b and x/y in the SDL mapping (default 1) |
| `GRAINBERNIK_ADVANCED` | `0` | Disable Sticks & Buttons |
| `GRAINBERNIK_MASK_POLL` | `0` | Do not hide claimed buttons from direct polling |
| `GRAINBERNIK_SAMPLE_DELETE` | `0` | Disable deleting recordings |
| `GRAINBERNIK_USB_AUDIO` | `0` | Disable the iPhone / USB audio adapter |
| `GRAINBERNIK_FIT`, `GRAINBERNIK_LEGACY_AUDIO` | `1` | Legacy beta 1.0 display / USB recording adapters |
| `GRAINBRICK_SCREEN`, `GRAINBRICK_SCALE` | e.g. `640x480`, `smooth`/`fast` | Native display options |

Log: `grainbrick beta 1.0.1/gb_launch.log`. Tests:
`python3 -m unittest discover -s tests` (native ARM64 tests are skipped elsewhere).

---

*Original README of GrainBrick below.*

# GrainBrick

A free granular ambient sound instrument for TrimUI Brick.

GrainBrick turns audio samples into evolving, organic textures with granular processing, tape-style sound shaping, effects and the ORBIX generative note engine.

It is designed for hands-on ambient exploration and sound design - not a tracker, sequencer or traditional looper.

## Official GrainBrick beta 1.0.1

This update adds adaptive resolution and controls, improved Anbernic compatibility and automatic USB audio input detection. RG40XX V is listed as tested by the author; RG40XX H is not.

## Features

- Granular sample processing and evolving ambient textures
- ORBIX generative note engine
- Reverb, delay, shimmer and other sound-shaping effects
- Tape-style processing
- Recording and trimming audio, including the Brick's internal microphone
- USB audio input/output support on compatible devices
- Project saving and contextual parameter help

## Download

Open the [original repository's Releases section](https://github.com/ETRNLIAM/GrainBrick/releases) and download:

GrainBrick_beta_1.0_TrimUI_Brick_KNULLI.zip

Do not download GitHub's automatically generated “Source code” ZIP - that is not the application.

## Compatibility

- Tested: original TrimUI Brick with KNULLI
- Requires a compatible AArch64 KNULLI installation providing Python 3.12, Pygame and NumPy
- Other handhelds, operating systems and TrimUI Brick Pro have not been confirmed compatible

## Installation

1. Download the release ZIP and extract its contents.
2. Copy both `grainbrick beta 1.0.1/` and `GrainBrick beta 1.0.1.sh` to `/userdata/roms/ports/`.
3. Refresh your PORTS list in KNULLI.
4. Launch GrainBrick beta 1.0.1.

When upgrading, preserve your samples, projects, recordings and settings. Keep the old folder until the updated release has been checked on your device.

## Feedback

This is a beta release. Please use the repository's Issues section to report reproducible bugs and hardware compatibility findings, including your OS version and device model.

## Licensing

GrainBrick is free to download, but its original application source code is currently closed. An open public beta does not mean that the GrainBrick source code is open source.

The distribution includes notices and applicable source materials for its bundled third-party components, including LGPL-licensed SoundTouch. See THIRD_PARTY_NOTICES.md, THIRD_PARTY_LICENSES/ and THIRD_PARTY_SOURCES/ inside the downloadable release.
