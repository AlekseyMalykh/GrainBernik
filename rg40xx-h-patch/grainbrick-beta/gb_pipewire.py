"""PipeWire routing for the iPhone USB Audio Gadget mode (ROCKNIX).

On systems where PipeWire owns the sound cards (ROCKNIX), GrainBrick cannot
open the gadget card directly. In iPhone mode:
  * output  -> 'gb_both', a PipeWire combine sink = built-in headphones/speaker
               + gadget (iPhone); PipeWire compensates the two clocks;
  * capture <- the gadget source (iPhone) through PipeWire;
  * monitor -> while recording from the iPhone, pw-loopback plays the iPhone
               input on the built-in output only (never back to the iPhone).
Also follows the headphone jack: ROCKNIX on the RG40XX H leaves the speaker
on with headphones plugged in.
Nothing here runs when PipeWire/pactl is absent (KNULLI keeps direct ALSA).
"""
import shutil
import subprocess
import threading
import time

BOTH = 'gb_both'
_available = None
_lock = threading.Lock()
_monitor = None
_recorders = set()
_jack_state = None


def _run(*args, timeout=3):
    try:
        out = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
        return out.returncode, out.stdout
    except (OSError, subprocess.SubprocessError):
        return 1, ''


def available():
    global _available
    if _available is None:
        _available = bool(shutil.which('pactl') and _run('pactl', 'info')[0] == 0)
    return _available


def _names(kind):
    code, out = _run('pactl', 'list', 'short', kind)
    if code:
        return []
    return [line.split('\t')[1] for line in out.splitlines() if '\t' in line]


def gadget_sink():
    return next((n for n in _names('sinks') if 'gadget' in n.lower() or 'uac2' in n.lower()), None)


def gadget_source():
    return next((n for n in _names('sources') if not n.endswith('.monitor')
                 and ('gadget' in n.lower() or 'uac2' in n.lower())), None)


def builtin_sink():
    return next((n for n in _names('sinks') if n != BOTH and 'gadget' not in n.lower()
                 and 'uac2' not in n.lower() and n.startswith('alsa_output')), None)


def ensure_both():
    """Create the combined output once; return its node name or None."""
    with _lock:
        if BOTH in _names('sinks'):
            return BOTH
        gadget, builtin = gadget_sink(), builtin_sink()
        if not gadget or not builtin:
            return None
        _run('pactl', 'set-sink-volume', gadget, '100%')
        _run('pactl', 'load-module', 'module-combine-sink', 'sink_name=' + BOTH,
             'slaves=%s,%s' % (builtin, gadget))
        for _ in range(20):
            if BOTH in _names('sinks'):
                return BOTH
            time.sleep(0.1)
    return None


def remove_both():
    code, out = _run('pactl', 'list', 'short', 'modules')
    for line in out.splitlines():
        parts = line.split('\t')
        if len(parts) > 2 and parts[1] == 'module-combine-sink' and 'sink_name=' + BOTH in parts[2]:
            _run('pactl', 'unload-module', parts[0])


def playback_pcm():
    sink = ensure_both()
    return 'pipewire:NODE=' + sink if sink else None


def capture_pcm():
    source = gadget_source()
    return 'pipewire:NODE=' + source if source else None


def monitor_running():
    return _monitor is not None and _monitor.poll() is None


def start_monitor():
    global _monitor
    with _lock:
        if monitor_running():
            return True
        source, sink = gadget_source(), builtin_sink()
        if not source or not sink or not shutil.which('pw-loopback'):
            return False
        try:
            _monitor = subprocess.Popen(['pw-loopback', '-C', source, '-P', sink,
                                         '--capture-props=node.name=gb_monitor_in',
                                         '--playback-props=node.name=gb_monitor_out'],
                                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except OSError:
            _monitor = None
            return False
        return True


def stop_monitor():
    global _monitor
    with _lock:
        proc, _monitor = _monitor, None
    if proc is not None and proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=1)
        except subprocess.TimeoutExpired:
            proc.kill()


def recording():
    return any(p.poll() is None for p in list(_recorders))


def track_recorder(process, monitor_wanted):
    """Monitor the iPhone input while this arecord runs (if wanted)."""
    _recorders.add(process)
    if monitor_wanted:
        start_monitor()

    def wait():
        try:
            process.wait()
        finally:
            _recorders.discard(process)
            if not recording():
                stop_monitor()
    threading.Thread(target=wait, name='gb-pw-recorder', daemon=True).start()


def follow_headphone_jack():
    """Mute the speaker while headphones are plugged in (card 0 controls)."""
    global _jack_state
    if not shutil.which('amixer'):
        return
    code, out = _run('amixer', '-c', '0', 'cget', "name=Headphone Jack", timeout=1)
    if code:
        return
    plugged = ': values=on' in out
    if plugged != _jack_state:
        _jack_state = plugged
        _run('amixer', '-c', '0', 'sset', 'Speaker', 'off' if plugged else 'on', timeout=1)
