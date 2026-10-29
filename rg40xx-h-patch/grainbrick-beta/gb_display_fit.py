# GrainBrick display adapter for Anbernik RG40XX H (640x480) and other
# KNULLI handhelds whose screen is smaller/larger than the TrimUI Brick
# (1024x768).
#
# The app draws its UI for the Brick resolution. This module intercepts
# pygame.display.set_mode(): the app gets an off-screen surface of the size
# it asked for, and every flip()/update() scales that surface to the real
# screen (keeping aspect ratio, letterboxing if needed).
#
# Environment variables (optional, set in "GrainBrick beta 1.0.sh"):
#   GRAINBRICK_SCREEN=640x480   force the real screen size (default: auto)
#   GRAINBRICK_SCALE=smooth     smooth (default, readable text) | fast
#   GRAINBRICK_FIT=0            disable the adapter completely
import os
import sys
import time

import pygame

_display = pygame.display
_orig_set_mode = _display.set_mode
_orig_flip = _display.flip
_orig_update = _display.update
_orig_get_surface = _display.get_surface

_state = {
    'real': None,     # actual display surface
    'virt': None,     # surface the app draws on (Brick size)
    'buf': None,      # scaled frame buffer
    'size': None,     # scaled size
    'offset': (0, 0),
    'smooth': os.environ.get('GRAINBRICK_SCALE', 'smooth').lower() != 'fast',
    'slow_frames': 0,
}


def _log(msg):
    print('GB DISPLAY FIT: ' + msg, flush=True)


def _parse_size(text):
    try:
        w, h = text.lower().replace('*', 'x').split('x')
        w, h = int(w), int(h)
        if w > 0 and h > 0:
            return w, h
    except Exception:
        pass
    return None


def _native_size():
    forced = _parse_size(os.environ.get('GRAINBRICK_SCREEN', ''))
    if forced:
        return forced
    if not _display.get_init():
        _display.init()
    try:
        sizes = _display.get_desktop_sizes()
        if sizes and sizes[0][0] > 0 and sizes[0][1] > 0:
            return tuple(sizes[0])
    except Exception:
        pass
    try:
        info = _display.Info()
        if info.current_w > 0 and info.current_h > 0:
            return info.current_w, info.current_h
    except Exception:
        pass
    return 640, 480


def set_mode(size=(0, 0), flags=0, *args, **kwargs):
    try:
        vw, vh = int(size[0]), int(size[1])
    except Exception:
        vw, vh = 0, 0
    nw, nh = _native_size()
    if vw <= 0 or vh <= 0 or (vw, vh) == (nw, nh):
        _state['virt'] = None
        _state['real'] = _orig_set_mode(size, flags, *args, **kwargs)
        return _state['real']

    real = _orig_set_mode((nw, nh), flags, *args, **kwargs)
    rw, rh = real.get_size()
    scale = min(rw / vw, rh / vh)
    dw, dh = max(1, int(round(vw * scale))), max(1, int(round(vh * scale)))
    virt = pygame.Surface((vw, vh), 0, 32)
    buf = pygame.Surface((dw, dh), 0, virt)
    real.fill((0, 0, 0))

    _state.update(real=real, virt=virt, buf=buf, size=(dw, dh),
                  offset=((rw - dw) // 2, (rh - dh) // 2), slow_frames=0)
    _log('app %dx%d -> screen %dx%d (scaled %dx%d, %s)' % (
        vw, vh, rw, rh, dw, dh, 'smooth' if _state['smooth'] else 'fast'))
    return virt


def _present():
    virt = _state['virt']
    if virt is None:
        return
    t0 = time.monotonic()
    buf = _state['buf']
    try:
        if _state['smooth']:
            pygame.transform.smoothscale(virt, _state['size'], buf)
        else:
            pygame.transform.scale(virt, _state['size'], buf)
    except Exception:
        buf = pygame.transform.scale(virt, _state['size'])
    _state['real'].blit(buf, _state['offset'])

    # If smooth scaling is too slow for this CPU, switch to fast scaling.
    if _state['smooth']:
        if time.monotonic() - t0 > 0.030:
            _state['slow_frames'] += 1
            if _state['slow_frames'] >= 30:
                _state['smooth'] = False
                _log('smooth scaling too slow, switching to fast')
        else:
            _state['slow_frames'] = 0


def flip():
    if _state['virt'] is not None:
        _present()
    return _orig_flip()


def update(*args, **kwargs):
    if _state['virt'] is not None:
        # Rectangles are in app coordinates; just present the whole frame.
        _present()
        return _orig_flip()
    return _orig_update(*args, **kwargs)


def get_surface():
    if _state['virt'] is not None:
        return _state['virt']
    return _orig_get_surface()


def install():
    if os.environ.get('GRAINBRICK_FIT', '1') == '0':
        _log('disabled')
        return
    _display.set_mode = set_mode
    _display.flip = flip
    _display.update = update
    _display.get_surface = get_surface
    _log('installed')
