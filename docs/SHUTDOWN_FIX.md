# Select + Start shutdown fix (ROCKNIX, 2026-11-06)

Tested over SSH on RG40XX H, official ROCKNIX 20261101, native GrainBrick
1.0.1, Python 3.12.16 and pygame 2.6.1. The existing v0.1.1-beta.1 release assets were refreshed with this fix.

## Diagnosis

Select + Start correctly produces EXIT. The hang happens during cleanup:

1. In a normal Wayland launch, GDB showed the main thread blocked in
   `pygame.quit -> mixer_quit -> Mix_CloseAudio`, waiting for SDL's PulseAudio
   audio thread. The last application messages were `SHUTTING DOWN...` and
   `SOUND PARAMS SAVED`. This was reproduced with actual gamepad input events
   written through evdev over SSH, rather than a synthetic EXIT action.
2. A separate real native DSP test exposed a blocked playback pipe:
   `engine.audio.write -> engine.audio_worker._audio_process_main`.
   Native `AudioWorker.stop()` returned while its child remained alive;
   Python's multiprocessing exit handler then waited indefinitely in `join()`.
   The inherited signal handling did not reliably terminate that worker.

## Changes

- The ROCKNIX launcher sets `SDL_AUDIODRIVER=dummy`. GrainBrick uses
  `aplay` / `arecord` for its actual audio, so its ALSA/PipeWire playback,
  recording and iPhone routing continue to use their existing backends.
  The unused pygame mixer no longer opens a PulseAudio stream.
- `gb_shutdown.py` retains native worker shutdown. If its timed graceful stop
  leaves a process alive, it freezes that worker to prevent aplay respawns,
  kills only its own playback children, then kills and joins the stuck worker.
  Linux pidfds protect against signalling a reused playback PID. ROCKNIX lacks
  `/proc/PID/task/PID/children`; a PPID scan of `/proc/*/stat` supplies the
  fallback. No PipeWire service or unrelated playback process is stopped.
- The ALSA enumeration unit fixture explicitly disables PipeWire discovery
  while using its fake Popen implementation, allowing it to run on ROCKNIX.

## Device verification

- Before fix: captured the mixer deadlock with GDB and the stuck DSP child's
  Python stack with faulthandler. Headless SDL dummy tests alone missed the
  mixer deadlock, so ordinary Wayland startup was also tested.
- After fix: normal installed launcher, restored sample, evdev Select + Start:
  `GRAINBRICK STOPPED`, launcher exit **0**.
- Repeated normal launch with evdev Start + Select: launcher exit **0**.
- No GrainBrick or aplay processes remained. CPU governor returned to
  `ondemand`.
- Separate native DSP test with intentionally stalled playback: recovery
  completed, no worker or aplay remained.
- On-device unittest discovery: **124 tests, OK, 28 skipped** (96 executed).
  The 28 optional native integration tests were not enabled in this suite;
  the native shutdown and ordinary launch checks above ran separately.
- New Linux regression tests exercise a real full pipe, a TERM-resistant
  audio worker/player, healthy shutdown, and an unloaded sample.

Device backup: `/storage/gb-select-start-backup-20261106-185120/`.
Installed changes: `gb_launch.py`, `gb_shutdown.py` in the app directory,
and `/storage/roms/ports/GrainBrick beta 1.0.1.sh`.
Device evidence: `/storage/gb-live-gdb.log`, `/storage/gb-exit-trace.log`,
`/storage/gb-exit-fixed3.log`, `/storage/gb-live-exit-status2`,
`/storage/gb-live-exit-status3`, `/storage/gb-fix-tests.log`.

An audible iPhone round-trip was not checked during this shutdown fix.
