# GrainBernik: USB audio input adapter for Anbernic RG40XX H (KNULLI).
#
# GrainBrick records with ALSA arecord from fixed devices chosen for the
# TrimUI Brick: "USB AUDIO" = hw:1,0 (exactly 48 kHz / 16 bit / stereo) and
# "BUILT-IN MIC" = hw:0,0. On the RG40XX H the USB card usually gets another
# number (card 1 is often HDMI), and many USB interfaces don't accept that
# exact format on a raw hw: device, so recording fails.
#
# This module rewrites the arecord device on the fly: "hw:1,0" becomes the
# first USB sound card that can record, opened through ALSA "plughw", which
# converts sample rate, bit depth and channel count automatically (a mono USB
# mic gives a stereo 48 kHz recording, as GrainBrick expects).
#
# Output needs no patch: GrainBrick already lists every sound card in its
# OUTPUT setting (INTERNAL / USB) and plays through plughw.
#
# Environment variables (optional):
#   GRAINBRICK_USB_IN=plughw:CARD=Device,DEV=0   force the capture device
#   GRAINBRICK_AUDIO=0                           disable this adapter
import os
import re
import subprocess
from pathlib import Path

ASOUND = Path('/proc/asound')
BRICK_USB_IN = 'hw:1,0'


def _log(msg):
    print('GB AUDIO: ' + msg, flush=True)


def usb_capture_cards():
    """[(card_number, card_id, name)] of USB sound cards that can record."""
    found = []
    try:
        text = (ASOUND / 'cards').read_text(encoding='utf-8', errors='replace')
    except Exception:
        return found
    for m in re.finditer(r'(?m)^\s*(\d+)\s+\[([^\]]+?)\s*\]:\s*(.+)$', text):
        num = int(m.group(1))
        card_dir = ASOUND / ('card%d' % num)
        if not (card_dir / 'usbid').exists() and 'usb' not in m.group(3).lower():
            continue
        if not any(card_dir.glob('pcm*c')):
            continue
        try:
            card_id = (card_dir / 'id').read_text().strip()
        except Exception:
            card_id = m.group(2).strip()
        dev = 0
        caps = sorted(card_dir.glob('pcm*c'))
        if caps:
            digits = re.findall(r'\d+', caps[0].name)
            dev = int(digits[0]) if digits else 0
        found.append((num, card_id, m.group(3).strip(), dev))
    return found


def usb_capture_device():
    forced = os.environ.get('GRAINBRICK_USB_IN', '').strip()
    if forced:
        return forced
    cards = usb_capture_cards()
    if not cards:
        return None
    num, card_id, name, dev = cards[0]
    if re.fullmatch(r'[A-Za-z0-9_]+', card_id or ''):
        return 'plughw:CARD=%s,DEV=%d' % (card_id, dev)
    return 'plughw:%d,%d' % (num, dev)


def _rewrite(args):
    """Return (new_args, old_device, new_device) for an arecord call."""
    if isinstance(args, (list, tuple)):
        argv = list(args)
        if not argv or os.path.basename(str(argv[0])) != 'arecord':
            return args, None, None
        for i, a in enumerate(argv):
            a = str(a)
            if a in ('-D', '--device') and i + 1 < len(argv):
                if str(argv[i + 1]) == BRICK_USB_IN:
                    new = usb_capture_device()
                    if new:
                        argv[i + 1] = new
                        return argv, BRICK_USB_IN, new
            elif a.startswith('--device=') and a.split('=', 1)[1] == BRICK_USB_IN:
                new = usb_capture_device()
                if new:
                    argv[i] = '--device=' + new
                    return argv, BRICK_USB_IN, new
            elif a.startswith('-D') and a[2:] == BRICK_USB_IN:
                new = usb_capture_device()
                if new:
                    argv[i] = '-D' + new
                    return argv, BRICK_USB_IN, new
        return args, None, None
    if isinstance(args, str) and re.match(r'\s*(\S*/)?arecord\b', args) and BRICK_USB_IN in args:
        new = usb_capture_device()
        if new:
            return args.replace(BRICK_USB_IN, new), BRICK_USB_IN, new
    return args, None, None


_OrigPopen = subprocess.Popen


class _Popen(_OrigPopen):
    def __init__(self, args, *a, **kw):
        new_args, old, new = _rewrite(args)
        if new:
            _log('arecord %s -> %s' % (old, new))
        elif isinstance(args, (list, tuple)) and args and os.path.basename(str(args[0])) == 'arecord':
            if BRICK_USB_IN in [str(x) for x in args]:
                _log('arecord %s: no USB capture card found' % BRICK_USB_IN)
        super().__init__(new_args, *a, **kw)


def install():
    if os.environ.get('GRAINBRICK_AUDIO', '1') == '0':
        _log('disabled')
        return
    subprocess.Popen = _Popen
    cards = usb_capture_cards()
    if cards:
        _log('installed; USB capture: ' + ', '.join(
            'card %d [%s] %s' % (n, i, name) for n, i, name, _ in cards))
    else:
        _log('installed; no USB capture card connected right now')
