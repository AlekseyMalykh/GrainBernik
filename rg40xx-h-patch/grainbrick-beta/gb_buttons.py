# GrainBernik: button layout adapter for Anbernic RG40XX H (KNULLI).
#
# GrainBrick expects the raw joystick button numbers of the TrimUI Brick and
# shows hints with Brick labels (A, B, X, Y, L1 ...). Other devices report
# different numbers, so the hints don't match the buttons you press.
#
# This module translates the device's raw button numbers into Brick numbers
# inside pygame.event.get(), using a mapping recorded once by a short
# calibration screen ("press A", "press B", ...). After that, the physical
# button labelled A on the device acts as A in GrainBrick, and so on.
#
# Mapping file: grainbrick-beta/gb_buttons.json
# Re-run calibration: launch "GrainBernik Buttons Setup.sh" from PORTS,
# or delete gb_buttons.json.
# Disable: GRAINBRICK_BUTTONS=0
import json
import os
import sys
import time
from pathlib import Path

import pygame

APP = Path(__file__).resolve().parent
MAP_FILE = APP / 'gb_buttons.json'
VERSION = 1

# Raw button numbers GrainBrick uses on the TrimUI Brick
# (engine/button_mapping.py DEFAULT_BINDINGS / PHYSICAL_LABELS).
BRICK = {
    'B': 4, 'A': 5, 'Y': 6, 'X': 7,
    'L1': 8, 'R1': 9, 'L2': 10, 'R2': 11,
    'SELECT': 12, 'START': 13, 'MENU': 14,
    'TAB-': 15, 'TAB+': 16,
}
DIRS = {'UP': (0, 1), 'DOWN': (0, -1), 'LEFT': (-1, 0), 'RIGHT': (1, 0)}

# (target, on-screen prompt, optional)
STEPS = [
    ('A', 'Press  A', False),
    ('B', 'Press  B', False),
    ('X', 'Press  X', False),
    ('Y', 'Press  Y', False),
    ('L1', 'Press  L1', False),
    ('R1', 'Press  R1', False),
    ('L2', 'Press  L2', False),
    ('R2', 'Press  R2', False),
    ('SELECT', 'Press  SELECT', False),
    ('START', 'Press  START', False),
    ('MENU', 'Press  MENU  (function button)', True),
    ('UP', 'Press  D-PAD UP', False),
    ('DOWN', 'Press  D-PAD DOWN', False),
    ('LEFT', 'Press  D-PAD LEFT', False),
    ('RIGHT', 'Press  D-PAD RIGHT', False),
    ('TAB-', 'TAB-:  press L3 (left stick click)', True),
    ('TAB+', 'TAB+:  press R3 (right stick click)', True),
]
SKIP_REQUIRED = 15.0
SKIP_OPTIONAL = 6.0
AXIS_ON = 0.6
AXIS_OFF = 0.3


def _log(msg):
    print('GB BUTTONS: ' + msg, flush=True)


# ---------------------------------------------------------------- calibration
def calibrate():
    pygame.init()
    pygame.joystick.init()
    if pygame.joystick.get_count() == 0:
        _log('no joystick, calibration skipped')
        return None
    joy = pygame.joystick.Joystick(0)
    joy.init()
    name = joy.get_name()
    try:
        info = pygame.display.Info()
        size = (info.current_w, info.current_h) if info.current_w > 0 else (640, 480)
    except Exception:
        size = (640, 480)
    screen = pygame.display.set_mode(size, pygame.FULLSCREEN)
    pygame.mouse.set_visible(False)
    w, h = screen.get_size()
    big = pygame.font.Font(None, max(32, h // 9))
    small = pygame.font.Font(None, max(20, h // 20))
    clock = pygame.time.Clock()

    buttons, dpad, axes = {}, {}, {}
    used = set()
    dpad_is_hat = False

    def draw(prompt, step, left):
        screen.fill((12, 12, 14))
        lines = [
            (small, 'GrainBernik  -  button setup  (%d/%d)' % (step, len(STEPS)), (150, 150, 150)),
            (big, prompt, (240, 220, 150)),
            (small, 'Skip in %d s' % max(0, int(left + 0.99)), (110, 110, 110)),
            (small, name[:40], (80, 80, 80)),
        ]
        ys = [h * 0.18, h * 0.42, h * 0.70, h * 0.88]
        for (font, text, col), y in zip(lines, ys):
            surf = font.render(text, True, col)
            screen.blit(surf, ((w - surf.get_width()) // 2, int(y)))
        pygame.display.flip()

    def wait_release(timeout=1.5):
        end = time.monotonic() + timeout
        while time.monotonic() < end:
            pygame.event.pump()
            pressed = any(joy.get_button(i) for i in range(joy.get_numbuttons()))
            hats = any(joy.get_hat(i) != (0, 0) for i in range(joy.get_numhats()))
            axs = any(abs(joy.get_axis(i)) > AXIS_OFF and i in axes.values()
                      for i in range(joy.get_numaxes()))
            if not (pressed or hats or axs):
                break
            clock.tick(60)
        pygame.event.clear()

    rest = [joy.get_axis(i) for i in range(joy.get_numaxes())]

    for n, (target, prompt, optional) in enumerate(STEPS, 1):
        if target in DIRS and dpad_is_hat:
            continue
        limit = SKIP_OPTIONAL if optional else SKIP_REQUIRED
        start = time.monotonic()
        result = None
        while result is None:
            left = limit - (time.monotonic() - start)
            if left <= 0:
                _log('skipped ' + target)
                break
            draw(prompt, n, left)
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    pygame.display.quit()
                    return None
                if ev.type == pygame.JOYBUTTONDOWN and ev.button not in used:
                    result = ('button', ev.button)
                elif ev.type == pygame.JOYHATMOTION and target in DIRS and ev.value != (0, 0):
                    result = ('hat', ev.value)
                elif (ev.type == pygame.JOYAXISMOTION and target in ('L2', 'R2')
                      and abs(ev.value - rest[ev.axis]) > AXIS_ON
                      and ev.axis not in axes.values()):
                    result = ('axis', ev.axis)
                if result:
                    break
            clock.tick(30)
        if result is None:
            continue
        kind, val = result
        if kind == 'button':
            used.add(val)
            if target in DIRS:
                dpad[str(val)] = target
            else:
                buttons[str(val)] = BRICK[target]
        elif kind == 'hat':
            dpad_is_hat = True
        elif kind == 'axis':
            axes[target] = val
        _log('%s -> %s %s' % (target, kind, val))
        wait_release()

    data = {
        'version': VERSION,
        'device': name,
        'buttons': buttons,       # raw device button -> Brick button
        'dpad_buttons': dpad,     # raw device button -> direction
        'trigger_axes': {BRICK[k]: v for k, v in axes.items()},  # Brick button -> axis
        'axis_rest': rest,
    }
    tmp = MAP_FILE.with_suffix('.tmp')
    tmp.write_text(json.dumps(data, indent=2), encoding='utf-8')
    os.replace(tmp, MAP_FILE)
    _log('saved ' + str(MAP_FILE))

    screen.fill((12, 12, 14))
    surf = big.render('Saved', True, (150, 220, 150))
    screen.blit(surf, ((w - surf.get_width()) // 2, h // 2 - surf.get_height() // 2))
    pygame.display.flip()
    time.sleep(1.0)
    pygame.display.quit()
    return data


# ---------------------------------------------------------------- translation
class _Translator:
    def __init__(self, data):
        self.buttons = {int(k): int(v) for k, v in data.get('buttons', {}).items()}
        self.dpad = {int(k): v for k, v in data.get('dpad_buttons', {}).items()}
        self.axes = {int(k): int(v) for k, v in data.get('trigger_axes', {}).items()}
        rest = data.get('axis_rest') or []
        self.rest = {a: (rest[a] if a < len(rest) else 0.0) for a in self.axes.values()}
        self.axis_down = {b: False for b in self.axes}
        self.dirs_held = set()

    def _hat_event(self, ev):
        x = (1 if 'RIGHT' in self.dirs_held else 0) - (1 if 'LEFT' in self.dirs_held else 0)
        y = (1 if 'UP' in self.dirs_held else 0) - (1 if 'DOWN' in self.dirs_held else 0)
        d = {'joy': getattr(ev, 'joy', 0), 'hat': 0, 'value': (x, y)}
        if hasattr(ev, 'instance_id'):
            d['instance_id'] = ev.instance_id
        return pygame.event.Event(pygame.JOYHATMOTION, d)

    def translate(self, events):
        out = []
        for ev in events:
            t = ev.type
            if t in (pygame.JOYBUTTONDOWN, pygame.JOYBUTTONUP):
                b = ev.button
                if b in self.dpad:
                    direction = self.dpad[b]
                    if t == pygame.JOYBUTTONDOWN:
                        self.dirs_held.add(direction)
                    else:
                        self.dirs_held.discard(direction)
                    out.append(self._hat_event(ev))
                    continue
                d = dict(ev.dict)
                d['button'] = self.buttons.get(b, 100 + b)
                out.append(pygame.event.Event(t, d))
            elif t == pygame.JOYAXISMOTION and ev.axis in self.rest:
                out.append(ev)
                for brick, axis in self.axes.items():
                    if axis != ev.axis:
                        continue
                    delta = abs(ev.value - self.rest[axis])
                    if not self.axis_down[brick] and delta > AXIS_ON:
                        self.axis_down[brick] = True
                        out.append(self._button(ev, pygame.JOYBUTTONDOWN, brick))
                    elif self.axis_down[brick] and delta < AXIS_OFF:
                        self.axis_down[brick] = False
                        out.append(self._button(ev, pygame.JOYBUTTONUP, brick))
            else:
                out.append(ev)
        return out

    @staticmethod
    def _button(ev, t, b):
        d = {'joy': getattr(ev, 'joy', 0), 'button': b}
        if hasattr(ev, 'instance_id'):
            d['instance_id'] = ev.instance_id
        return pygame.event.Event(t, d)


def _load():
    try:
        data = json.loads(MAP_FILE.read_text(encoding='utf-8'))
        if data.get('version') == VERSION:
            return data
    except Exception:
        pass
    return None


def install():
    if os.environ.get('GRAINBRICK_BUTTONS', '1') == '0':
        _log('disabled')
        return
    data = _load()
    if data is None:
        _log('no mapping, starting calibration')
        data = calibrate()
    if not data:
        _log('no mapping, buttons not translated')
        return
    tr = _Translator(data)
    ev_mod = pygame.event
    orig_get, orig_poll, orig_wait = ev_mod.get, ev_mod.poll, ev_mod.wait

    def get(*args, **kwargs):
        return tr.translate(orig_get(*args, **kwargs))

    def poll():
        res = tr.translate([orig_poll()])
        return res[0] if res else pygame.event.Event(pygame.NOEVENT)

    def wait(*args, **kwargs):
        res = tr.translate([orig_wait(*args, **kwargs)])
        return res[0] if res else pygame.event.Event(pygame.NOEVENT)

    ev_mod.get, ev_mod.poll, ev_mod.wait = get, poll, wait
    _log('installed for %s: %d buttons, %d d-pad buttons, %d trigger axes' % (
        data.get('device', '?'), len(tr.buttons), len(tr.dpad), len(tr.axes)))


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'calibrate':
        calibrate()
