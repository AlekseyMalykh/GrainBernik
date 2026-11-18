# GrainBernik on official GrainBrick BETA 2.0 — port status

Branch `beta2-port`. Beta 2.0 (tag `v2.0.0-beta.2`, 17 Nov 2026) is a different
package from 1.0.1: plain Python sources (`main.py`, `engine/`, `ui/`) instead of a
compiled `main` module, installed separately as `grainbrick-beta2/` with its own
launcher. The official files are **not** redistributed here; build a package from
your own copy of `GrainBrick_BETA_2_0.zip`.

## Step 1: minimal launch on RG40XX H / ROCKNIX

- `rg40xx-h-patch/grainbrick-beta2/gb_launch.py` — bootstrap (Python 3.12, ARM64,
  bundled NumPy 1.26.4 check) that loads `gb_shutdown` and imports the official `main.py`.
- `rocknix/GrainBrick BETA 2.0.sh` — ROCKNIX launcher: separate Python in
  `/storage/grainbrick-python`, `SDL_AUDIODRIVER=dummy`, ABXY swap for the SDL
  controller mapping, performance governor while running.
- `rocknix/make_package.sh` and `install.sh` accept either official ZIP
  (1.0.1 or BETA 2.0) and detect it. Re-installing BETA 2.0 keeps the user's
  samples, projects, recordings and settings files.

### What is intentionally NOT loaded yet

| Adapter | Reason |
|---|---|
| `gb_buttons` | BETA 2.0 has the same SDL-controller input as 1.0.1 (off on ROCKNIX). |
| `gb_recording` | BETA 2.0's `AudioRecorder.stop` repairs WAV headers itself. |
| `gb_display_fit`, `gb_audio` | Native display and USB-capture handling, as in 1.0.1. |
| `gb_quick_settings`, `gb_samples` | Refuse to attach: BETA 2.0 extends `ControlManager.SETTINGS_PARAMS` (color theme, CPU performance, debug logs, output boost, MIDI, tempo, BLE) and their guards accept only the 1.0.1 list. Step 2b. |
| `gb_advanced` (1.0.1) | Replaced by `gb_advanced2` (step 3). |

### Verified without a device

- Hook points used by the loaded adapter exist in the BETA 2.0 sources
  (`AudioWorker.stop`, `self.process`, `main.py` runs on import).
- Package build and the installer's data-keeping logic on the official ZIP.
- Not run: the app itself. The native libraries are ARM64 only; there is no
  on-device result for BETA 2.0 yet.

## Step 2: iPhone / USB audio

- `rg40xx-h-patch/grainbrick-beta2/gb_usb_settings.py` — **SETTINGS → IPHONE / USB AUDIO**
  (MODE, SEND TO IPHONE, RECORD FROM IPHONE, STATUS). BETA 2.0 builds SETTINGS from a
  scrolling list, so the key and row are appended **last**, after the RHYTHM / BLE
  integration has added its own (`SETTINGS_PARAMS` and `gb_extra_settings_rows` must stay aligned).
  The page uses the native INFO panel (`get_context_info` wrapper) and footer.
- Shared engine hooks (`gb_usb_audio.install_engine_hooks`, also used by 1.0.1) now also cover
  BETA 2.0: `create_capture_route` keeps the PipeWire target for the gadget; only the stereo
  pair 1/2 is offered for it (PipeWire owns the card); the direct USB record worker
  `gb_usb_record_fx35.py` is guarded like `arecord` (stops on unplug / mode change).
- Controls follow the native "Console Controls" contract of BETA 2.0: **A** opens the page and
  starts editing MODE, **B** ends the edit / leaves the page, **LEFT/RIGHT** change the value while
  editing, **hold A + LEFT/RIGHT** changes it at once (released A does nothing more). ON/OFF fields
  toggle with A (A+LEFT = OFF, A+RIGHT = ON). All later pages (presets, Advanced Settings) must use it.
- Monitoring while recording is native in BETA 2.0 (REC screen), so the old SELECT-toggled
  `pw-loopback` monitor and the MONITOR option are not used.
- External USB devices (e.g. M-VAVE FM1, Zoom H1n) use the native BETA 2.0 path; the adapter
  does not touch them.
- Settings file `gb_usb_audio.json` is kept on re-install and migrated from a 1.0.1 install.

## Step 3: STICKS & BUTTONS (Advanced Settings)

New SETTINGS row `STICKS & BUTTONS` (last row, after RHYTHM/BLE/IPHONE). Assigns
left/right stick X/Y, L2/R2 (Hold/Toggle effects) and L3/R3 (stick clicks) to
sound parameters, with factory presets and a User slot. Same
`grainbernik_advanced` block in `settings.json` as the 1.0.1 version, so
existing assignments are kept (ids that do not exist in 2.0 are dropped).

Console Controls: A opens a submenu / starts editing a value (ON/OFF rows flip
at once), B leaves (first ends editing), LEFT/RIGHT change a value being
edited, A held + LEFT/RIGHT (quick change) changes the focused value without
entering edit mode. L/R/TAB are blocked while the page is open.

Differences from the 1.0.1 adapter:
- Buttons come from the engine's `AutoKeyAdapter` output (virtual L2=10, R2=11,
  L3=15, R3=16); no SDL mapping parsing, no polling proxy (2.0 never polls
  buttons). L3/R3 are owned on every screen while ON; L2/R2 on GRAIN/FX/TAPE/
  VISUAL only, and only with an effect.
- The row/key are registered lazily through `gb_settings_rows`, shared with the
  USB page, so the key list and renderer rows stay aligned in any order.
- No NAV_FIX wrap hack (2.0 wraps the SETTINGS list natively).

New content (every id verified against the real 2.0 `ParameterBus`, 253 ids):
- Axes (61): GRAIN 2/3 (pitch spread, size/timing random, reverse chance,
  envelope), roam, delay/reverb/shimmer/tape, ORBIX, **ORBIX Rings** (structure,
  brightness, damping, position, mix, tune, detune, stereo, noise, excite),
  **OSCILLATOR** (blend, dry/wet, drive, x-mod, balance, level), **tempo**
  (BPM, offset), **LIVE** input and master level. Removed: filter.*, tape.speed,
  pan (not parameters in 2.0).
- Button effects: Scatter, Reverse Grains, Rings Bloom/Damp/Detune, Osc On/
  Drive/FM, Slow Down/Speed Up (relative BPM), Tempo +5/-5 (steps), Input Cut,
  Input Boost, Mute Out, besides the 1.0.1 effects.
- Presets: Granular, Ambient, Texture, Echo, Tape, ORBIX Play (as before) and
  **Rhythm, Rings, Oscillator, Live, Grain 2/3**.

Limits: RHYTHM pattern parameters live in the rhythm app, not in the
ParameterBus, so only the shared tempo is assignable. A Hold effect on tempo
fights Link/tap tempo while pressed.

Test: `GRAINBRICK_BETA2_ZIP=... python3 -m pytest tests/test_beta2_advanced.py`.

## Steps still to do

2b. Quick settings and deleting recorded samples from inside the app.
4. Performance check on the H700 (Rings resonator, LIVE), BLE MIDI on ROCKNIX; then release.

Test with the official package:
`GRAINBRICK_BETA2_ZIP=/path/to/GrainBrick_BETA_2_0.zip python3 -m unittest tests.test_beta2_port -v`
