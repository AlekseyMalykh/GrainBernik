"""Run the real official 1.0.1 main loop/DSP with fake ALSA command-line tools.

Usage: python3 tests/native_usb_flow.py /path/to/official/grainbrick-directory
Requires Linux ARM64 Python 3.12 (qemu is supported), Pygame, SDL dummy drivers.
Uses disposable configs, samples and fake controllers, never a physical PCM.
Run in a separate process from unittest suites because main has global state.
"""
import importlib
import os
import sys
import tempfile
import wave
import math
import struct
import time
import json
from pathlib import Path
import platform
if len(sys.argv) != 2 or platform.machine().lower() not in ('aarch64', 'arm64') or sys.version_info[:2] != (3, 12):
    print('SKIP: pass official 1.0.1 directory on ARM64 Python 3.12')
    raise SystemExit(0)
app = Path(sys.argv[1]).resolve()
repo = Path(__file__).resolve().parents[1]
if not (app / '_vendor').is_dir():
    raise SystemExit('Requires official 1.0.1 with _vendor')
test_temp = tempfile.TemporaryDirectory(prefix='gb-usb-flow-')
root = Path(test_temp.name)
sys.path[:0] = [str(repo / 'rg40xx-h-patch/grainbrick-beta'), str(app), str(app / '_vendor')]
os.environ['GRAINBRICK_ROOT'] = str(root)
for source in app.glob('*.so*'):
    (root / source.name).symlink_to(source)
for name in ('samples', 'demo-samples'):
    (root / name).mkdir()
    with wave.open(str(root / name / 'tone.wav'), 'wb') as f:
        f.setparams((2, 2, 48000, 0, 'NONE', ''))
        f.writeframes(b''.join((struct.pack('<hh', int(3000 * math.sin(2 * math.pi * 440 * i / 48000)), int(3000 * math.sin(2 * math.pi * 440 * i / 48000))) for i in range(48000))))
bin = root / 'bin'
bin.mkdir()
os.environ['PATH'] = str(bin) + ':' + os.environ['PATH']
(bin / 'aplay').write_text('''#!/usr/bin/python3
import sys,time
from pathlib import Path
log=Path(__file__).parent.parent/'aplay.log'
with log.open('a') as f:
 f.write(str(time.time())+' START '+repr(sys.argv)+'\\n');f.flush()
 n=0
 while b:=sys.stdin.buffer.read(4096):
  n+=len(b)
  if n%40960==0:f.write(str(time.time())+' BYTES '+str(n)+'\\n');f.flush()
 f.write(str(time.time())+' END\\n')
''')
(bin / 'aplay').chmod(493)
(bin / 'arecord').write_text('''#!/usr/bin/python3
import sys,time,wave,signal,struct
from pathlib import Path
running=True
def stop(*a):
 global running
 running=False
signal.signal(signal.SIGINT,stop);signal.signal(signal.SIGTERM,stop)
log=(Path(__file__).parent.parent/'arecord.log').open('a');log.write(str(time.time())+' START '+repr(sys.argv)+'\\n');log.flush()
with wave.open(sys.argv[-1],'wb') as f:
 f.setparams((2,2,48000,0,'NONE',''))
 while running:
  f.writeframes(struct.pack('<hh',1000,-1000)*4800);time.sleep(.1)
log.write(str(time.time())+' END\\n');log.close()
''')
(bin / 'arecord').chmod(493)
import pygame

class Joy:

    def init(self):
        pass

    def quit(self):
        pass

    def get_name(self):
        return 'Integration controller'

    def get_numaxes(self):
        return 4

    def get_axis(self, i):
        return 0.0
pygame.joystick.get_count = lambda: 1
pygame.joystick.Joystick = lambda i: Joy()
import gb_usb_audio as audio, gb_usb_gadget as gadget, gb_usb_settings as usb, gb_advanced as advanced
audio.CONFIG = root / 'gb_usb_audio.json'
cfg = dict(audio.DEFAULT)
cfg['mode'] = audio.MODES[2]
audio.Settings().save(cfg)
fixture = gadget.System(root / 'system', '4.9.fixture')
for path, text in [('proc/asound/card7/id', 'UAC2_Gadget'), ('proc/asound/cards', '7 [UAC2_Gadget ]: UAC2_Gadget - Gadget\n'), ('proc/asound/card7/pcm0c/sub0/status', 'closed'), ('proc/asound/card7/pcm0p/sub0/status', 'closed'), ('sys/class/udc/udc0/state', 'configured')]:
    p = fixture.path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)
usb.Monitor = lambda: audio.Monitor(fixture)
real_init = pygame.init
state = {'frame': 0, 'start': 0, 'started': False, 'stopped': False}

def init():
    audio.install_engine_hooks(system=fixture)
    advanced._attach()
    usb._attach()
    from engine.input import InputManager

    def poll(self, *args, **kwargs):
        from types import SimpleNamespace
        state['frame'] += 1
        n = state['frame']
        m = sys.modules['main']
        if n == 1:
            m.load_sample(SimpleNamespace(path=str(root / 'samples/tone.wav'), name='tone.wav', is_dir=False))
            assert m.audio_worker is not None, 'Native sample/DSP worker did not load'
            return [('START', None)]
        if n == 10:
            m.open_input_recording_page()
        if n == 12:
            m.record_source_index = next((i for i, s in enumerate(m.RECORD_SOURCES) if 'usb' in repr(s).lower()))
            m.start_input_recording()
            state['start'] = time.monotonic()
            print('RECORDING STATE', m.record_mode, m.audio_worker.running, flush=True)
            assert m.record_mode == 'recording' and m.audio_worker.running
            state['started'] = True
        if m.record_mode == 'recording' and time.monotonic() - state['start'] > 2:
            m.stop_input_recording_to_editor()
            assert m.record_mode == 'edit' and m.audio_worker.running
            state['stopped'] = True
        if n > 200 or (state['start'] and time.monotonic() - state['start'] > 4):
            return [('EXIT', None)]
        return []
    InputManager.poll = poll
    return real_init()
pygame.init = init
try:
    importlib.import_module('main')
    assert state['started'] and state['stopped'], 'Native recording flow did not complete'
    play = (root / 'aplay.log').read_text().splitlines()
    record = (root / 'arecord.log').read_text().splitlines()
    assert 'plughw:CARD=UAC2_Gadget,DEV=0' in record[0]
    assert any(('plughw:CARD=UAC2_Gadget,DEV=0' in line and 'START' in line for line in play))
    start, end = (float(record[0].split()[0]), float(record[-1].split()[0]))
    during = [line for line in play if 'BYTES' in line and start < float(line.split()[0]) < end]
    assert len(during) >= 2, 'Playback did not progress while native capture was running'
    assert record[-1].endswith(' END') and play[-1].endswith(' END'), 'Native child processes did not stop'
    wavs = list((root / 'recordings').glob('*.wav'))
    assert wavs
    metrics = audio.wav_metrics(wavs[0])
    assert metrics['non_silent']
    result = {'native_record_flow': True, 'playback_progress_during_capture': len(during), 'capture': metrics, 'alsa': 'mocked subprocess tools; no real USB endpoints', 'iphone_verified': False, 'children_stopped': True}
    if os.environ.get('GRAINBERNIK_TEST_OUTPUT'):
        out = Path(os.environ['GRAINBERNIK_TEST_OUTPUT'])
        out.mkdir(parents=True, exist_ok=True)
        (out / 'native-usb-flow.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))
except BaseException as exc:
    print('FLOW ERROR', repr(exc), flush=True)
    raise
finally:
    test_temp.cleanup()
