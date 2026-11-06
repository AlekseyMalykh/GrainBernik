"""Real 1.0.1 recording -> editor -> Save and Use, with a bad arecord header.

Run separately on ARM64 Python 3.12 with pygame and NumPy:
  python3 tests/native_recording_save.py /path/to/official/app
All app data and fake ALSA tools live in a disposable directory.
"""
import importlib
import os
from pathlib import Path
import sys
import tempfile
import time
import wave

app = Path(sys.argv[1]).resolve()
real_fm1 = "--real-fm1" in sys.argv[2:]
repo = Path(__file__).resolve().parents[1]
temp = tempfile.TemporaryDirectory(prefix='gb-save-flow-')
root = Path(temp.name)
os.environ.update(GRAINBRICK_ROOT=str(root), SDL_VIDEODRIVER='dummy', SDL_AUDIODRIVER='dummy')
sys.path[:0] = [str(repo / 'rg40xx-h-patch/grainbrick-beta'), str(app), str(app / '_vendor')]
for source in app.glob('*.so*'):
    (root / source.name).symlink_to(source)
if (app / 'resources').exists():
    (root / 'resources').symlink_to(app / 'resources')
(root / 'samples').mkdir()
bin_dir = root / 'bin'
bin_dir.mkdir()
os.environ['PATH'] = str(bin_dir) + ':' + os.environ['PATH']

# Deliberately leave arecord's placeholder on disk even after stop. The input
# waveform is real PCM; only its lengths are wrong, as in the FM1 failure.
recorder = bin_dir / ('arecord-fixture' if real_fm1 else 'arecord')
recorder.write_text('''#!%s
import math, signal, struct, sys, time
f = open(sys.argv[-1], 'wb')
f.write(struct.pack('<4sI4s4sIHHIIHH4sI', b'RIFF', 0x80000024, b'WAVE',
                    b'fmt ', 16, 1, 2, 48000, 192000, 4, 16, b'data', 0x80000000))
for i in range(48000):
    n = int(4000 * math.sin(2 * math.pi * 440 * i / 48000))
    f.write(struct.pack('<hh', n, n))
f.flush()
def stop(*args):
    f.close()
    raise SystemExit(0)
signal.signal(signal.SIGINT, stop)
signal.signal(signal.SIGTERM, stop)
while True: time.sleep(.01)
''' % sys.executable)
player = bin_dir / 'aplay'
player.write_text('#!%s\nimport sys\nwhile sys.stdin.buffer.read(4096): pass\n' % sys.executable)
recorder.chmod(0o755)
player.chmod(0o755)

import pygame
import gb_recording
gb_recording.install()
original_init = pygame.init
state = {'frame': 0, 'started': None, 'saved': False}


def init():
    gb_recording._attach()
    inputs = sys.modules['engine.audio_inputs']
    old_captures = inputs.available_usb_captures

    def captures(*args, **kwargs):
        return [{'card': 1, 'device_number': 0, 'card_id': 'FM1',
                 'label': 'ChoralRoot FM-1 fixture', 'pcm': 'plughw:CARD=FM1,DEV=0'}]

    for name, module in list(sys.modules.items()):
        if module is not None and (name == 'main' or name.startswith('engine.')):
            if getattr(module, 'available_usb_captures', None) is old_captures:
                module.available_usb_captures = captures
    from engine.input import InputManager

    def poll(self, *args, **kwargs):
        m = sys.modules['main']
        state['frame'] += 1
        if state['frame'] == 3:
            m.open_input_recording_page()
            m.record_source_index = next(i for i, s in enumerate(m.RECORD_SOURCES) if 'usb' in repr(s).lower())
            m.start_input_recording()
            assert m.record_mode == 'recording'
            state['started'] = time.monotonic()
        if state['started'] and not state['saved'] and time.monotonic() - state['started'] > (2 if real_fm1 else 1):
            m.stop_input_recording_to_editor()
            assert m.record_mode == 'edit', m.record_mode
            raw = next((root / 'recordings').glob('*.wav'))
            with wave.open(str(raw)) as reader:
                state['input_frames'] = reader.getnframes()
                assert 24000 <= reader.getnframes() <= 144000 if real_fm1 else reader.getnframes() == 48000, reader.getnframes()
            # This is the exact native action invoked by A in the editor.
            m.save_recording_and_use()
            saved = list((root / 'samples/recordings').glob('*.wav'))
            assert len(saved) == 1, saved
            with wave.open(str(saved[0])) as reader:
                assert state['input_frames'] * .9 <= reader.getnframes() <= state['input_frames']
                non_silent = any(reader.readframes(reader.getnframes()))
                print('SAVED NON-SILENT:', non_silent, flush=True)
                if not real_fm1:
                    assert non_silent, 'Saved PCM is silent'
            assert m.audio_worker is not None, 'Saved recording was not loaded'
            state['saved'] = True
            print('PASS: native A / Save and Use loaded the finalized recording', flush=True)
            return [('EXIT', 1)]
        if state['frame'] > 600:
            raise AssertionError('Recording flow timed out')
        return []

    InputManager.poll = poll
    return original_init()


pygame.init = init
try:
    importlib.import_module('main')
    assert state['saved']
finally:
    temp.cleanup()
