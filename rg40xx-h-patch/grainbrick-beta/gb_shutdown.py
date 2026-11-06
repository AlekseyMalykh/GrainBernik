"""Finish native 1.0.1 shutdown when a USB/PipeWire playback pipe stalls.

The native worker's timed stop can leave its process alive. Python then joins
that process without a timeout at interpreter exit. Only this worker and its
own aplay children are eligible for recovery; system audio is never stopped.
"""
import os
from pathlib import Path
import signal
import sys

_installed = _attached = False


def _playback_children(pid):
    """Snapshot direct aplay children while the worker still owns them."""
    if not pid:
        return []
    try:
        children = Path('/proc/%d/task/%d/children' % (pid, pid)).read_text().split()
    except OSError:
        # ROCKNIX H700 omits CONFIG_CHECKPOINT_RESTORE and hence /children.
        children = []
        for entry in Path('/proc').glob('[0-9]*'):
            try:
                fields = (entry / 'stat').read_text().rpartition(')')[2].split()
                if int(fields[1]) == pid:
                    children.append(entry.name)
            except (OSError, ValueError, IndexError):
                continue
    result = []
    for child in children:
        try:
            child = int(child)
            command = Path('/proc/%d/cmdline' % child).read_bytes().split(b'\0')[0]
            if os.path.basename(os.fsdecode(command)) == 'aplay':
                # pidfds prevent a reused PID from targeting another process.
                result.append(os.pidfd_open(child))
        except (OSError, ValueError, AttributeError):
            continue
    return result


def _signal_playback(handles, sig):
    for handle in handles:
        try:
            signal.pidfd_send_signal(handle, sig)
        except ProcessLookupError:
            pass


def _stop_worker(worker, original_stop, *args, **kwargs):
    process = getattr(worker, 'process', None)
    handles = _playback_children(process.pid) if process is not None else []
    try:
        result = original_stop(worker, *args, **kwargs)
        if process is not None and process.is_alive():
            print('GB SHUTDOWN: recovering stalled audio worker', flush=True)
            # Native stop has exhausted its graceful waits. Freeze the worker
            # before taking another snapshot: write() can respawn aplay after
            # a broken pipe, including during the native termination attempt.
            try:
                os.kill(process.pid, signal.SIGSTOP)
            except ProcessLookupError:
                pass
            handles.extend(_playback_children(process.pid))
            _signal_playback(handles, signal.SIGKILL)
            process.kill()
            process.join(timeout=1)
            if process.is_alive():
                raise RuntimeError('GrainBernik audio worker did not stop')
        return result
    finally:
        for handle in handles:
            os.close(handle)


def _attach():
    global _attached
    if _attached:
        return True
    module = sys.modules.get('engine.audio_worker')
    if module is None:
        return False
    cls = module.AudioWorker
    original_stop = cls.stop

    def stop(self, *args, **kwargs):
        return _stop_worker(self, original_stop, *args, **kwargs)

    cls.stop = stop
    _attached = True
    return True


def install():
    global _installed
    if _installed:
        return
    import pygame
    original_init = pygame.init

    def init(*args, **kwargs):
        _attach()
        return original_init(*args, **kwargs)

    pygame.init = init
    _installed = True
