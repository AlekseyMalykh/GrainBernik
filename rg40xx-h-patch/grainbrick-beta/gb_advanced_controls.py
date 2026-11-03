"""Configuration and control modulation; no Pygame or DSP dependency.

GrainBrick beta 1.0 exposes ParameterBus.params/get/set. Parameter bounds come
from the running engine, never from guessed DSP ranges. Sources compose in a
stable order: left stick, right stick, L2, R2. Releasing one source preserves
the others and restores the underlying parameter when its last owner leaves.
"""
import json
import math
import os
from pathlib import Path

CONFIG_KEY = 'grainbernik_advanced'
VERSION = 1
CONTROLS = ('left_stick', 'right_stick', 'l2', 'r2')
AXIS_PARAMETERS = (
    ('grain.position', 'Grain Position'), ('grain.size', 'Grain Size'),
    ('grain.density', 'Grain Density'), ('grain.pitch', 'Grain Pitch'),
    ('grain.spray', 'Grain Spray'), ('filter.cutoff', 'Filter Cutoff'),
    ('filter.resonance', 'Filter Resonance'), ('delay.time', 'Delay Time'),
    ('delay.feedback', 'Delay Feedback'), ('delay.mix', 'Delay Mix'),
    ('reverb.mix', 'Reverb Mix'), ('reverb.size', 'Reverb Size'),
    ('shimmer.mix', 'Shimmer Amount'), ('tape.speed', 'Tape Speed'),
    ('pan', 'Pan'), ('roam.speed', 'Roam Speed'),
    ('tape.saturation', 'Tape Saturation'), ('tape.wow', 'Tape Wow'),
    ('tape.flutter', 'Tape Flutter'), ('reverb.decay', 'Reverb Decay'),
    ('delay.lowpass', 'Delay Lowpass'), ('shimmer.shift', 'Shimmer Pitch'),
    ('orbix.gravity', 'ORBIX Gravity'), ('orbix.rotation', 'ORBIX Rotation'),
    ('orbix.bounce', 'ORBIX Bounce'), ('orbix.volume', 'ORBIX Volume'),
    ('orbix.attack', 'ORBIX Attack'), ('orbix.release', 'ORBIX Release'),
    ('orbix.reverb', 'ORBIX Reverb'), ('orbix.balls', 'ORBIX Balls'),
    ('orbix.root', 'ORBIX Root'), ('orbix.scale', 'ORBIX Scale'),
    ('orbix.instrument', 'ORBIX Instrument'), ('orbix.octave', 'ORBIX Octave'),
    ('orbix.shape', 'ORBIX Shape'),
)
# These parameters are enumerations/counts in the native ORBIX engine.
# Smooth the gesture internally, then publish only valid integer selections.
DISCRETE_PARAMETERS = frozenset(('orbix.balls', 'orbix.root', 'orbix.scale',
                                  'orbix.instrument', 'orbix.octave', 'orbix.shape'))
# These are reversible presets of existing engine parameters, not new DSP.
# Freeze is the native Motion Hold fragment texture, not a spectral freeze.
BUTTON_EFFECTS = {
    'Freeze': {'grain.enabled': 1, 'motion.enabled': 1, 'motion.hold': 1},
    'Reverse': {'motion.enabled': 1, 'motion.reverse': 1},
    'Delay Throw': {'delay.mix': .65, 'delay.feedback': .6},
    'Reverb Wash': {'reverb.mix': .85, 'reverb.size': .95, 'reverb.decay': 12},
    'Pitch Drop': {'grain.enabled': 1, 'grain.pitch': -12},
    'Bypass': {'delay.mix': 0, 'reverb.mix': 0, 'shimmer.mix': 0,
               'tape.enabled': 0, 'comp.enabled': 0,
               **{key: 0 for key in ('eq.low', 'eq.lmid', 'eq.mid',
                                     'eq.hmid', 'eq.high', 'eq.air')}},
    'ORBIX': {'orbix.enabled': 1},
}


def defaults():
    sticks = {}
    for name, axes in (('left_stick', (0, 1)), ('right_stick', (2, 3))):
        sticks[name] = dict(enabled=False, x=None, y=None, deadzone=12,
                            sensitivity=100, invert_x=False, invert_y=False,
                            mode='Spring', smoothing=60, axis_x=axes[0], axis_y=axes[1])
    return dict(version=VERSION, **sticks,
                l2=dict(enabled=False, effect=None, mode='Hold'),
                r2=dict(enabled=False, effect=None, mode='Hold'))


def _number(value, low, high, fallback):
    if isinstance(value, bool):
        return fallback
    try:
        value = float(value)
        return max(low, min(high, value)) if math.isfinite(value) else fallback
    except (TypeError, ValueError, OverflowError):
        return fallback


def validate(raw):
    result = defaults()
    if not isinstance(raw, dict) or raw.get('version', VERSION) != VERSION:
        return result
    for name in CONTROLS:
        src = raw.get(name)
        if not isinstance(src, dict):
            continue
        dst = result[name]
        dst['enabled'] = src.get('enabled') is True
        if name.endswith('stick'):
            for key in ('x', 'y'):
                v = src.get(key)
                dst[key] = v if isinstance(v, str) and v in dict(AXIS_PARAMETERS) else None
            for key, lo, hi in (('deadzone', 0, 50), ('sensitivity', 10, 200),
                                ('smoothing', 0, 500), ('axis_x', 0, 31), ('axis_y', 0, 31)):
                dst[key] = int(_number(src.get(key), lo, hi, dst[key]))
            for key in ('invert_x', 'invert_y'):
                dst[key] = src.get(key) is True
            dst['mode'] = 'Latch' if src.get('mode') == 'Latch' else 'Spring'
        else:
            effect = src.get('effect')
            dst['effect'] = effect if isinstance(effect, str) and effect in BUTTON_EFFECTS else None
            dst['mode'] = 'Toggle' if src.get('mode') == 'Toggle' else 'Hold'
    return result


class Settings:
    """Merge into the existing settings.json; never replace unknown app keys."""
    def __init__(self, path):
        self.path = Path(path)
        self.error = ''
        self.data = defaults()
        try:
            self.data = validate(self._read().get(CONFIG_KEY))
        except (OSError, ValueError, TypeError) as exc:
            self.error = 'Settings read failed: ' + str(exc)

    def _read(self):
        if not self.path.exists():
            return {}
        obj = json.loads(self.path.read_text(encoding='utf-8'))
        if not isinstance(obj, dict):
            raise ValueError('settings.json must contain an object')
        return obj

    def save(self, preserved=None):
        # A malformed existing document must not be silently erased.
        temp = self.path.with_name(self.path.name + '.advanced.tmp')
        try:
            obj = {**(preserved or {}), **self._read()}
            obj[CONFIG_KEY] = self.data
            with temp.open('w', encoding='utf-8') as stream:
                json.dump(obj, stream, ensure_ascii=False, indent=2, allow_nan=False)
                stream.write('\n')
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temp, self.path)
            self.error = ''
            return True
        except (OSError, ValueError, TypeError) as exc:
            self.error = 'Settings save failed: ' + str(exc)
            try:
                temp.unlink(missing_ok=True)
            except OSError:
                pass
            return False


class Controls:
    def __init__(self, bus, settings):
        self.bus = bus
        self.settings = settings
        self.sources = {}  # ordered source id -> {parameter: absolute value}
        self.base = {}
        self.written = {}
        self.gestures = {}
        self.pressed = set()
        self.toggled = set()
        self.blocked = set()
        self.center_required = set()
        self.last_time = None

    def bounds(self, key):
        param = self.bus.params.get(key)
        if param is None:
            return None
        lo, hi = float(param.minimum), float(param.maximum)
        if math.isfinite(lo) and math.isfinite(hi) and hi > lo:
            return lo, hi
        return None

    def axis_choices(self):
        return [(None, 'None')] + [(k, label) for k, label in AXIS_PARAMETERS if self.bounds(k)]

    def effect_choices(self):
        return [None] + [name for name, preset in BUTTON_EFFECTS.items()
                         if all(self.bounds(k) for k in preset)]

    def _external_changes(self):
        for key, previous in self.written.items():
            value = self.bus.get(key)
            if abs(value - previous) > 1e-8:
                self.base[key] = value

    def _apply(self):
        combined = {}
        for name in CONTROLS:
            for source in (name + '.x', name + '.y', name):
                combined.update(self.sources.get(source, {}))
        for key in combined:
            self.base.setdefault(key, self.bus.get(key))
        for key in set(self.written) | set(combined):
            target = combined.get(key, self.base.get(key, self.bus.get(key)))
            bounds = self.bounds(key)
            if bounds:
                target = max(bounds[0], min(bounds[1], target))
            if key in DISCRETE_PARAMETERS and key in combined:
                target = float(round(target))
            if abs(self.bus.get(key) - target) > 1e-8:
                self.bus.set(key, target)
            if key in combined:
                self.written[key] = self.bus.get(key)
            else:
                self.written.pop(key, None)
                self.base.pop(key, None)

    def cancel(self, name=None):
        """Immediately unwind transient FX, including Toggle and Latch.

        A held button cannot re-engage on returning from a menu. Stick input
        must pass through center before a new gesture can start.
        """
        self._external_changes()
        names = CONTROLS if name is None else (name,)
        for control in names:
            for source in (control, control + '.x', control + '.y'):
                self.sources.pop(source, None)
                self.gestures.pop(source, None)
            self.toggled.discard(control)
            if control in self.pressed:
                self.blocked.add(control)
            if control.endswith('stick'):
                self.center_required.add(control)
        self._apply()

    def button(self, name, down, performance=True):
        cfg = self.settings.data[name]
        if not down:
            self.pressed.discard(name)
            self.blocked.discard(name)
            if cfg['mode'] == 'Hold':
                self._external_changes()
                self.sources.pop(name, None)
                self._apply()
            return
        if name in self.pressed:
            return
        self.pressed.add(name)
        if not performance or not cfg['enabled'] or name in self.blocked:
            return
        if cfg['effect'] not in self.effect_choices():
            return
        self._external_changes()
        if cfg['mode'] == 'Toggle' and name in self.toggled:
            self.toggled.remove(name)
            self.sources.pop(name, None)
        elif cfg['effect'] is not None:
            self.sources[name] = dict(BUTTON_EFFECTS[cfg['effect']])
            if cfg['mode'] == 'Toggle':
                self.toggled.add(name)
        self._apply()

    def tick(self, axes, now, performance=True, excluded_axes=()):
        self._external_changes()
        dt = 1 / 60 if self.last_time is None else max(0, min(.1, now - self.last_time))
        self.last_time = now
        if not performance:
            self.cancel()
            return
        for name in CONTROLS:
            cfg = self.settings.data[name]
            if not name.endswith('stick'):
                if not cfg['enabled'] and name in self.sources:
                    self.cancel(name)
                continue
            # Unassigned or unavailable axes must not disable the other axis.
            physical = (cfg['axis_x'], cfg['axis_y'])
            if not cfg['enabled']:
                if any(name + '.' + a in self.sources for a in ('x', 'y')):
                    self.cancel(name)
                continue
            valid = [cfg[a] is not None and i not in excluded_axes and i in axes
                     for a, i in zip(('x', 'y'), physical)]
            if physical[0] == physical[1] and all(valid):
                valid = [False, False]
            raw = [_number(axes[i], -1, 1, 0) if ok else 0 for i, ok in zip(physical, valid)]
            zone = cfg['deadzone'] / 100
            if name in self.center_required:
                if any(abs(v) > zone for v in raw):
                    continue
                self.center_required.discard(name)
            for axis, value, available in zip(('x', 'y'), raw, valid):
                source = name + '.' + axis
                key = cfg[axis]
                bounds = self.bounds(key)
                if not available or bounds is None:
                    self.sources.pop(source, None)
                    self.gestures.pop(source, None)
                    continue
                magnitude = max(0, (abs(value) - zone) / (1 - zone))
                signed = math.copysign(magnitude, value)
                if cfg['invert_' + axis]:
                    signed = -signed
                state = self.gestures.get(source)
                if state is None:
                    if not magnitude:
                        continue
                    current = self.bus.get(key)
                    state = self.gestures[source] = dict(base=current, value=current, active=False)
                if magnitude:
                    if not state['active'] and cfg['mode'] == 'Latch':
                        state['base'] = state['value']
                    target = state['base'] + signed * cfg['sensitivity'] / 100 * (bounds[1] - bounds[0]) / 2
                    target = max(bounds[0], min(bounds[1], target))
                else:
                    target = state['base'] if cfg['mode'] == 'Spring' else state['value']
                state['active'] = bool(magnitude)
                alpha = 1 if not cfg['smoothing'] else -math.expm1(-dt * 1000 / cfg['smoothing'])
                state['value'] += (target - state['value']) * alpha
                tolerance = max(1e-8, (bounds[1] - bounds[0]) * 1e-5)
                if abs(state['value'] - target) < tolerance:
                    state['value'] = target
                self.sources[source] = {key: state['value']}
                if not magnitude and cfg['mode'] == 'Spring' and state['value'] == target:
                    self.sources.pop(source, None)
                    self.gestures.pop(source, None)
        self._apply()


class Menu:
    """Physical-button navigation model; renderer uses the same row data."""
    LABELS = dict(left_stick='Left Stick', right_stick='Right Stick', l2='L2 Button', r2='R2 Button')

    def __init__(self, settings, controls):
        self.settings, self.controls = settings, controls
        self.page = None
        self.index = 0
        self.parent_index = 0
        self.confirm = False

    def open(self):
        self.controls.cancel()
        self.page, self.index, self.confirm = 'root', 0, False

    def rows(self):
        if self.confirm:
            return [('cancel', 'Cancel', ''), ('restore', 'Restore Defaults', '')]
        if self.page == 'root':
            return [(name, label, 'ON' if self.settings.data[name]['enabled'] else 'OFF')
                    for name, label in self.LABELS.items()] + [('reset', 'Reset to Defaults', '>'), ('back', 'Back', '')]
        name = self.page.split('.')[0]
        cfg = self.settings.data[name]
        if self.page.endswith('.options'):
            return [('deadzone', 'Deadzone', str(cfg['deadzone']) + '%'),
                    ('sensitivity', 'Sensitivity', str(cfg['sensitivity']) + '%'),
                    ('invert_x', 'Invert X', 'ON' if cfg['invert_x'] else 'OFF'),
                    ('invert_y', 'Invert Y', 'ON' if cfg['invert_y'] else 'OFF'),
                    ('mode', 'Return Mode', cfg['mode']),
                    ('smoothing', 'Smoothing', str(cfg['smoothing']) + ' ms'),
                    ('axis_x', 'Physical X Axis', str(cfg['axis_x'])),
                    ('axis_y', 'Physical Y Axis', str(cfg['axis_y'])), ('back', 'Back', '')]
        result = [('enabled', 'Enabled', 'ON' if cfg['enabled'] else 'OFF')]
        if name.endswith('stick'):
            labels = dict(self.controls.axis_choices())
            result += [(a, a.upper() + ' Effect', labels.get(cfg[a], 'Unavailable')) for a in ('x', 'y')]
            result += [('options', 'Stick Options', '>')]
        else:
            effect = cfg['effect'] or 'None'
            if cfg['effect'] not in self.controls.effect_choices():
                effect = 'Unavailable'
            result += [('effect', 'Effect', effect), ('mode', 'Mode', cfg['mode'])]
        return result + [('back', 'Back', '')]

    def back(self):
        if self.confirm:
            self.confirm, self.index = False, 4
        elif self.page.endswith('.options'):
            self.page, self.index = self.page.split('.')[0], 3
        elif self.page != 'root':
            self.page, self.index = 'root', self.parent_index
        else:
            self.page, self.index = None, 0

    def handle(self, action):
        if self.page is None:
            return False
        if action in ('B', 'MENU', 'REBIND_CANCEL', 'TAB_PREV'):
            self.back()
            return True
        if action in ('UP', 'DOWN'):
            self.index = (self.index + (1 if action == 'DOWN' else -1)) % len(self.rows())
            return True
        if action not in ('A', 'LEFT', 'RIGHT'):
            return True
        key = self.rows()[self.index][0]
        direction = -1 if action == 'LEFT' else 1
        if self.confirm:
            if action == 'A':
                if key == 'restore':
                    self.controls.cancel()
                    self.settings.data = defaults()
                    self.settings.save()
                self.confirm, self.index = False, 4
            return True
        if key == 'back':
            self.back()
        elif self.page == 'root':
            if key == 'reset':
                self.confirm, self.index = True, 0
            else:
                self.parent_index = self.index
                self.page, self.index = key, 0
        elif key == 'options':
            self.page, self.index = self.page + '.options', 0
        else:
            name = self.page.split('.')[0]
            cfg = self.settings.data[name]
            self.controls.cancel(name)
            if key in ('enabled', 'invert_x', 'invert_y'):
                cfg[key] = not cfg[key]
            elif key in ('x', 'y', 'effect', 'mode'):
                if key in ('x', 'y'):
                    choices = [k for k, _ in self.controls.axis_choices()]
                elif key == 'effect':
                    choices = self.controls.effect_choices()
                else:
                    choices = ['Spring', 'Latch'] if name.endswith('stick') else ['Hold', 'Toggle']
                old = choices.index(cfg[key]) if cfg[key] in choices else 0
                cfg[key] = choices[(old + direction) % len(choices)]
            else:
                low, high, step = {'deadzone': (0, 50, 1), 'sensitivity': (10, 200, 5),
                                   'smoothing': (0, 500, 10), 'axis_x': (0, 31, 1), 'axis_y': (0, 31, 1)}[key]
                cfg[key] = max(low, min(high, cfg[key] + direction * step))
            self.settings.save()
        return True
