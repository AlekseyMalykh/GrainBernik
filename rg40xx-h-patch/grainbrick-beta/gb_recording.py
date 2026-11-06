"""Finalize stopped arecord WAVs before the native recording editor opens.

Interrupted USB capture can leave arecord's 0x80000000 data-length placeholder
in a small file. The native editor trusts it and allocates gigabytes on Save.
Only the native recorder's completed output is eligible for header repair.
"""
import os
from pathlib import Path
import struct
import sys

_installed = _attached = False


def finalize_wav(path):
    """Validate PCM frames, repair oversized RIFF/data lengths without reading PCM.

    Call only after the writer has stopped. Valid data chunks keep their size,
    so a trailing metadata chunk is never mistaken for additional audio.
    """
    with Path(path).open('r+b') as stream:
        size = os.fstat(stream.fileno()).st_size
        header = stream.read(12)
        if len(header) != 12 or header[:4] != b'RIFF' or header[8:] != b'WAVE':
            raise ValueError('Recording is not a RIFF WAV file')
        if size - 8 > 0xffffffff:
            raise ValueError('Recording exceeds the RIFF WAV size limit')
        block = None
        while stream.tell() + 8 <= size:
            chunk_offset = stream.tell()
            kind, length = struct.unpack('<4sI', stream.read(8))
            available = size - stream.tell()
            if kind == b'fmt ':
                if length < 16 or length > available:
                    raise ValueError('Invalid recording format chunk')
                fmt, channels, rate, byte_rate, block, bits = struct.unpack('<HHIIHH', stream.read(16))
                if (fmt != 1 or channels < 1 or bits not in (8, 16, 24, 32)
                        or block != channels * (bits // 8) or not rate or byte_rate != rate * block):
                    raise ValueError('Unsupported recording PCM format')
            elif kind == b'data':
                if block is None:
                    raise ValueError('Recording has no PCM format')
                # A zero size can also be left by an interrupted writer.
                actual = available if length > available or length == 0 else length
                actual -= actual % block
                if actual == 0:
                    raise ValueError('Recording contains no complete audio frames')
                changed = False
                if actual != length:
                    stream.seek(chunk_offset + 4)
                    stream.write(struct.pack('<I', actual))
                    changed = True
                if struct.unpack_from('<I', header, 4)[0] != size - 8:
                    stream.seek(4)
                    stream.write(struct.pack('<I', size - 8))
                    changed = True
                if changed:
                    stream.flush()
                    os.fsync(stream.fileno())
                return actual // block, changed
            if length > available:
                raise ValueError('Truncated recording WAV chunk')
            stream.seek(chunk_offset + 8 + length + (length & 1))
        raise ValueError('Recording has no audio data chunk')


def _attach():
    global _attached
    if _attached:
        return True
    module = sys.modules.get('engine.audio_recorder')
    if module is None:
        return False
    cls = module.AudioRecorder
    original_stop = cls.stop

    def stop(self, *args, **kwargs):
        process = getattr(self, '_process', None)
        path = original_stop(self, *args, **kwargs)
        if not path:
            return path
        try:
            if process is not None and process.poll() is None:
                raise ValueError('Recording process has not stopped')
            frames, changed = finalize_wav(path)
            if changed:
                print('GB RECORDING: finalized WAV header, %d frames' % frames, flush=True)
        except (OSError, ValueError) as exc:
            self.last_error = str(exc)
            print('GB RECORDING: cannot open recording: %s' % exc, flush=True)
            return None
        return path

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
