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
| `gb_advanced`, `gb_quick_settings`, `gb_samples` | Refuse to attach: BETA 2.0 extends `ControlManager.SETTINGS_PARAMS` (color theme, CPU performance, debug logs, output boost, MIDI, tempo, BLE) and their guards accept only the 1.0.1 list. Step 3. |

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
- Monitoring while recording is native in BETA 2.0 (REC screen), so the old SELECT-toggled
  `pw-loopback` monitor and the MONITOR option are not used.
- External USB devices (e.g. M-VAVE FM1, Zoom H1n) use the native BETA 2.0 path; the adapter
  does not touch them.
- Settings file `gb_usb_audio.json` is kept on re-install and migrated from a 1.0.1 install.

## Steps still to do

2b. Quick settings and deleting recorded samples from inside the app.
3. Advanced Settings (L3/R3, presets) and ORBIX assignments against the new ORBIX / RHYTHM UI.
4. Performance check on the H700 (Rings resonator, LIVE), BLE MIDI on ROCKNIX; then release.

Test with the official package:
`GRAINBRICK_BETA2_ZIP=/path/to/GrainBrick_BETA_2_0.zip python3 -m unittest tests.test_beta2_port -v`
