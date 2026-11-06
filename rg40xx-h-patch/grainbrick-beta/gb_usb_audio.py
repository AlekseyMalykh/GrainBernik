"""Direct GrainBrick USB gadget PCM routing; no bridge or system ALSA changes."""
import argparse
import copy
import json
import math
import os
from pathlib import Path
import re
import struct
import subprocess
import threading
import time
import wave

from gb_usb_gadget import System, atomic_json
import gb_pipewire

MODES = ('Disabled', 'External USB Audio', 'iPhone USB Audio Gadget')
DEFAULT = {'mode': MODES[0], 'input': True, 'output': True, 'rate': 'Auto',
           'channels': 2, 'card_id': '', 'capture_device': None, 'playback_device': None,
           'previous_output': 'internal', 'monitor': True}
CONFIG = Path(__file__).with_name('gb_usb_audio.json')


class AudioError(RuntimeError):
    pass


class Settings:
    def __init__(self, path=None):
        self.path, self.error = Path(path if path is not None else CONFIG), ''
        self.data = self.load()

    def load(self):
        data = copy.deepcopy(DEFAULT)
        try:
            saved = json.loads(self.path.read_text(encoding='utf-8'))
            if not isinstance(saved, dict):
                raise ValueError('USB settings must be an object')
            data.update({k: v for k, v in saved.items() if k in data})
            if data['mode'] not in MODES or data['rate'] not in ('Auto', '48000 Hz'):
                raise ValueError('Unsupported USB mode/rate')
            if (type(data['input']) is not bool or type(data['output']) is not bool
                    or type(data['monitor']) is not bool or data['channels'] != 2):
                raise ValueError('Invalid USB direction/channel settings')
            if not isinstance(data['card_id'], str) or not isinstance(data['previous_output'], str):
                raise ValueError('Invalid ALSA ID')
            for key in ('capture_device', 'playback_device'):
                if data[key] is not None and (type(data[key]) is not int or data[key] < 0):
                    raise ValueError('Invalid PCM number')
        except FileNotFoundError:
            pass
        except (OSError, ValueError, TypeError) as exc:
            self.error = str(exc)
            return copy.deepcopy(DEFAULT)
        return data

    def save(self, data):
        try:
            atomic_json(self.path, data)
        except OSError as exc:
            self.error = str(exc)
            return False
        self.data, self.error = copy.deepcopy(data), ''
        return True


def endpoints(system, config):
    """Require an unambiguous gadget identity and explicit PCM if ambiguous."""
    cards = [c for c in system.cards() if c['gadget']]
    if config['card_id']:
        cards = [c for c in cards if c['id'] == config['card_id']]
    if len(cards) != 1:
        if cards:
            raise AudioError('Unsupported Configuration: select card_id in gb_usb_audio.json')
        support = [system.function_support(k)['state'] for k in ('uac1', 'uac2')]
        if all(s == 'disabled' for s in support):
            raise AudioError('Driver Not Available: no UAC driver evidence')
        if any(s in ('candidate', 'present') for s in support):
            raise AudioError('Audio Device Not Detected: gadget not active')
        raise AudioError('Driver Status Unknown: no gadget ALSA card')
    card = cards[0]
    if not re.fullmatch(r'[A-Za-z0-9_]+', card['id'] or ''):
        raise AudioError('Unsupported Configuration: invalid stable ALSA card ID')
    result = {'card': card}
    for direction, key in (('capture', 'input'), ('playback', 'output')):
        matches = [p for p in card['pcms'] if p['direction'] == direction]
        requested = config[direction + '_device']
        if requested is not None:
            matches = [p for p in matches if p['device'] == requested]
        if config[key] and len(matches) != 1:
            raise AudioError('Unsupported Configuration: %s PCM %s' % (
                direction, 'ambiguous; select device number' if matches else 'unavailable'))
        if matches:
            result[direction] = {**matches[0], 'pcm': 'plughw:CARD=%s,DEV=%d' %
                                 (card['id'], matches[0]['device'])}
    return result


def connected(system):
    # Configured means USB host enumeration; never claim it identifies iPhone.
    return connection_status(system) == 'USB Connected'


def connection_status(system):
    udcs = system.udcs()
    if any(u['state'] == 'configured' for u in udcs):
        return 'USB Connected'
    if not udcs or any(u['state'] is None for u in udcs):
        return 'USB Status Unknown'
    return 'USB Not Connected'


def _descendant(system, pid, ancestor):
    for _ in range(16):
        if pid == ancestor:
            return True
        try:
            stat = (system.path('/proc') / str(pid) / 'stat').read_text()
            pid = int(stat.rsplit(')', 1)[1].split()[1])
        except (OSError, ValueError, IndexError):
            return False
        if pid <= 1:
            return False
    return False


class Monitor:
    """Read PCM progress, not merely enumeration. No test stream steals PCM."""
    def __init__(self, system=None, app_pid=None):
        self.system, self.app_pid = system or System(), app_pid or os.getpid()
        self.previous = {}

    def status(self, config):
        if config['mode'] != MODES[2]:
            self.previous.clear()
            return config['mode'], 'Native Audio'
        if not connected(self.system):
            self.previous.clear()
            return connection_status(self.system), 'Streams Stopped'
        try:
            route = endpoints(self.system, config)
        except AudioError as exc:
            self.previous.clear()
            return 'USB Connected', str(exc)
        active, busy, now = set(), False, time.monotonic()
        current = {}
        for direction, key in (('capture', 'input'), ('playback', 'output')):
            if not config[key]:
                continue
            for stream in route.get(direction, {}).get('substreams', []):
                text = stream['status'] or ''
                owner = re.search(r'owner_pid\s*:\s*(\d+)', text)
                pointer = re.search(r'hw_ptr\s*:\s*(\d+)', text)
                own = bool(owner and _descendant(self.system, int(owner[1]), self.app_pid))
                running = bool(re.search(r'state\s*:\s*RUNNING', text))
                busy |= bool(owner and not own)
                if running and own and pointer:
                    identity = (stream['path'], int(owner[1]))
                    value = int(pointer[1])
                    previous = self.previous.get(identity)
                    if previous and previous[0] != value and now - previous[1] < 3:
                        active.add(direction)
                    current[identity] = (value, now)
        self.previous = current
        if active == {'capture', 'playback'}:
            return 'USB Connected', 'Full Duplex Active'
        if busy:
            return 'USB Connected', 'Audio Device Busy'
        if active:
            return 'USB Connected', 'Input Ready' if 'capture' in active else 'Output Ready'
        return 'USB Connected', 'Audio Device Detected'


def stop_process(process):
    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=0.5)
    except subprocess.TimeoutExpired:
        process.kill()
        try:
            process.wait(timeout=0.5)
        except subprocess.TimeoutExpired:
            pass  # An uninterruptible kernel syscall requires kernel recovery.


def guard(process, direction, settings_path=CONFIG, system=None):
    """A watcher in the same process (also the native forked audio worker).

    Terminates only our own child on unplug/mode change; unblocks native pipes.
    No watcher is started for external audio or the disabled mode.
    """
    system = system or System()

    def watch():
        while process.poll() is None:
            cfg = Settings(settings_path).data
            if cfg['mode'] != MODES[2] or not cfg[direction] or not connected(system):
                stop_process(process)
                return
            time.sleep(0.25)
    threading.Thread(target=watch, name='gb-usb-' + direction, daemon=True).start()


def install_engine_hooks(settings_path=None, system=None):
    """Attach verified 1.0.1 enumeration and Popen extension points.

    Existing DSP, worker buffering and recording editor stay in control.
    Caller must run after embedded engine modules exist, before main init.
    """
    import sys
    settings_path = settings_path if settings_path is not None else CONFIG
    system = system or System()
    inputs = sys.modules.get('engine.audio_inputs')
    devices = sys.modules.get('engine.audio_devices')
    if not inputs or not devices or not hasattr(inputs, 'available_usb_captures'):
        return False  # beta 1.0 needs a different recorder API, never guess.
    if getattr(inputs, '_grainbernik_usb', False):
        return True
    old_capture, old_outputs = inputs.available_usb_captures, devices.available_outputs
    inputs._grainbernik_native_captures = old_capture
    devices._grainbernik_native_outputs = old_outputs

    def captures(*args, **kwargs):
        cfg = Settings(settings_path).data
        if cfg['mode'] != MODES[2]:
            return old_capture(*args, **kwargs)
        if not cfg['input'] or not connected(system):
            return []
        try:
            route = endpoints(system, cfg)
            card, pcm = route['card'], route['capture']
            # ROCKNIX: PipeWire owns the card; record through it instead.
            target = gb_pipewire.capture_pcm() if gb_pipewire.available() else None
            return [{'card': card['number'], 'device_number': pcm['device'], 'card_id': card['id'],
                     'label': 'iPhone USB Gadget', 'pcm': target or pcm['pcm']}]
        except AudioError:
            return []

    def outputs(*args, **kwargs):
        existing = list(old_outputs(*args, **kwargs))
        # ROCKNIX's system default may remain on the iPhone gadget after a
        # disconnect. INTERNAL must address the console, not that stale sink.
        if gb_pipewire.available():
            builtin = gb_pipewire.builtin_sink()
            if builtin:
                existing = [(key, label, 'pipewire:NODE=' + builtin if key == 'internal' else pcm)
                            for key, label, pcm in existing]
        cfg = Settings(settings_path).data
        if cfg['mode'] != MODES[2] or not cfg['output'] or not connected(system):
            return existing
        try:
            route = endpoints(system, cfg)
            # ROCKNIX: one PipeWire output feeds headphones/speaker AND iPhone.
            target = gb_pipewire.playback_pcm() if gb_pipewire.available() else None
            if target:
                return existing + [('grainbernik_usb_gadget', 'IPHONE + PHONES', target)]
            return existing + [('grainbernik_usb_gadget', 'IPHONE', route['playback']['pcm'])]
        except AudioError:
            return existing

    # Compiled modules can retain `from ... import ...` references. Replace
    # all actual references, not just the original exporting module.
    for module in list(sys.modules.values()):
        if module is None:
            continue
        for name, old, new in (('available_usb_captures', old_capture, captures),
                               ('available_outputs', old_outputs, outputs)):
            if getattr(module, name, None) is old:
                setattr(module, name, new)

    original_popen = subprocess.Popen

    class USBPopen(original_popen):
        def __init__(self, args, *a, **kw):
            cfg, direction = Settings(settings_path).data, None
            if isinstance(args, (list, tuple)) and args and cfg['mode'] == MODES[2]:
                tool = os.path.basename(str(args[0]))
                # Only processes explicitly targeting the detected gadget. Never
                # reroute built-in capture, arbitrary shell commands or system audio.
                if tool in ('arecord', 'aplay'):
                    try:
                        route = endpoints(system, cfg)
                    except AudioError:
                        route = {}
                    key = 'capture' if tool == 'arecord' else 'playback'
                    pcm = route.get(key, {}).get('pcm')
                    prefix = 'pipewire:NODE=alsa_input' if key == 'capture' else 'pipewire:NODE=' + gb_pipewire.BOTH
                    if any(str(v).startswith(prefix) or str(v).startswith('-D' + prefix)
                           or str(v).startswith('--device=' + prefix) for v in args):
                        pcm = None
                        direction = 'input' if key == 'capture' else 'output'
                        if not cfg[direction] or not connected(system):
                            raise OSError('USB Not Connected or direction disabled')
                    if pcm and any(pcm == str(v) or str(v) in ('--device=' + pcm, '-D' + pcm) for v in args):
                        direction = 'input' if key == 'capture' else 'output'
                        if not cfg[direction] or not connected(system):
                            raise OSError('USB Not Connected or direction disabled')
            super().__init__(args, *a, **kw)
            if direction:
                guard(self, direction, settings_path, system)
                if direction == 'input' and gb_pipewire.available():
                    gb_pipewire.track_recorder(self, cfg['monitor'])

    subprocess.Popen = USBPopen
    inputs._grainbernik_usb = True
    return True


def wav_metrics(path):
    with wave.open(str(path), 'rb') as stream:
        if stream.getsampwidth() != 2:
            raise AudioError('Metrics require 16-bit PCM')
        count, total, peak = 0, 0, 0
        while data := stream.readframes(8192):
            for (value,) in struct.iter_unpack('<h', data):
                count += 1
                total += value * value
                peak = max(peak, abs(value))
        rms = math.sqrt(total / count) / 32768 if count else 0
        return {'samples': count, 'peak': peak / 32768, 'rms_dbfs': 20 * math.log10(max(rms, 1e-12)),
                'non_silent': bool(count and rms > 10 ** (-70 / 20))}


def pcm_test(directory, seconds=10, capture=True, playback=True, system=None, settings_path=CONFIG):
    """Explicit finite A/B/C/D ALSA test. Never enables input monitoring/loopback."""
    system = system or System()
    if not 1 <= seconds <= 600:
        raise AudioError('Test duration must be 1..600 seconds')
    cfg = Settings(settings_path).data
    if not connected(system):
        raise AudioError('USB Not Connected')
    cfg.update(input=capture, output=playback)
    route = endpoints(system, cfg)
    directory = Path(directory)
    if any((directory / name).exists() for name in
           ('tone.wav', 'capture.wav', 'capture.log', 'playback.log', 'results.json')):
        raise AudioError('Test files already exist; choose a new output directory')
    directory.mkdir(parents=True, exist_ok=True)
    rate, processes, logs = 48000, [], []
    if playback:
        with wave.open(str(directory / 'tone.wav'), 'wb') as stream:
            stream.setparams((2, 2, rate, 0, 'NONE', 'not compressed'))
            # -24 dBFS, two distinct tones; never copy capture to output.
            block = b''.join(struct.pack('<hh', int(2067 * math.sin(2 * math.pi * 440 * i / rate)),
                                        int(2067 * math.sin(2 * math.pi * 660 * i / rate))) for i in range(rate))
            for _ in range(seconds):
                stream.writeframesraw(block)
    results, error = {}, None
    try:
        for name, enabled, argv in (
            ('capture', capture, ['arecord', '-D', route.get('capture', {}).get('pcm', ''), '-t', 'wav',
                                  '-f', 'S16_LE', '-r', str(rate), '-c', '2', '-d', str(seconds),
                                  str(directory / 'capture.wav')]),
            ('playback', playback, ['aplay', '-D', route.get('playback', {}).get('pcm', ''),
                                    str(directory / 'tone.wav')])):
            if not enabled:
                continue
            log = (directory / (name + '.log')).open('w')
            logs.append(log)
            processes.append((name, subprocess.Popen(argv, stdout=subprocess.DEVNULL, stderr=log)))
        deadline = time.monotonic() + seconds + 5
        while any(p.poll() is None for _, p in processes):
            if any(p.poll() not in (None, 0) for _, p in processes):
                raise AudioError('PCM process failed; inspect capture/playback logs (device may be busy)')
            if time.monotonic() > deadline or not connected(system):
                raise AudioError('Test timed out or USB disconnected')
            time.sleep(0.1)
    except (AudioError, OSError) as exc:
        error = str(exc)
    finally:
        for _, process in processes:
            stop_process(process)
        for log in logs:
            log.close()
    for name, process in processes:
        results[name] = {'returncode': process.returncode}
    for name in results:
        log = (directory / (name + '.log')).read_text(errors='replace')
        results[name]['xrun_or_error'] = bool(re.search('overrun|underrun|xrun|error|busy', log, re.I))
    if capture:
        try:
            results.setdefault('capture', {}).update(wav_metrics(directory / 'capture.wav'))
        except (OSError, wave.Error, AudioError) as exc:
            results.setdefault('capture', {})['wav_error'] = str(exc)
            error = error or 'Capture WAV unavailable or invalid'
    if error:
        results['aborted'] = error
    results['iphone_recording_verified'] = False  # Requires listening/recording on physical iPhone.
    atomic_json(directory / 'results.json', results)
    if error:
        raise AudioError(error)
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--test', choices=('capture', 'playback', 'duplex'))
    parser.add_argument('--seconds', type=int, default=10)
    parser.add_argument('--directory', default='usb_audio_test')
    args = parser.parse_args()
    try:
        result = (pcm_test(args.directory, args.seconds, args.test != 'playback', args.test != 'capture')
                  if args.test else {'settings': Settings().data,
                                    'status': Monitor().status(Settings().data)})
        print(json.dumps(result, indent=2))
        if args.test and any(v.get('returncode', 0) or v.get('xrun_or_error', False)
                             or v.get('non_silent') is False for v in result.values() if isinstance(v, dict)):
            raise AudioError('PCM test failed; inspect results and logs')
    except (AudioError, OSError, ValueError, wave.Error) as exc:
        parser.exit(1, str(exc) + '\n')


if __name__ == '__main__':
    main()
