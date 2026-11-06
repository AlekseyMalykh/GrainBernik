"""Configuration and control modulation; no Pygame or DSP dependency.

GrainBrick beta 1.0 exposes ParameterBus.params/get/set. Parameter bounds come
from the running engine, never from guessed DSP ranges. Sources compose in a
stable order: left stick, right stick, L2, R2. Releasing one source preserves
the others and restores the underlying parameter when its last owner leaves.
L3/R3 (stick clicks) are separate button controls like L2/R2.
"""
import json
import math
import os
from pathlib import Path

CONFIG_KEY = 'grainbernik_advanced'
VERSION = 1
CONTROLS = ('left_stick', 'right_stick', 'l2', 'r2', 'l3', 'r3')
BUTTONS = ('l2', 'r2', 'l3', 'r3')
# Controls that existed before L3/R3; older User slots contain only these.
LEGACY_CONTROLS = ('left_stick', 'right_stick', 'l2', 'r2')
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
AXIS_IDS = frozenset(key for key, label in AXIS_PARAMETERS)
# These parameters are enumerations/counts in the native ORBIX engine.
# Smooth the gesture internally, then publish only valid integer selections.
DISCRETE_PARAMETERS = frozenset(('orbix.balls', 'orbix.root', 'orbix.scale',
                                  'orbix.instrument', 'orbix.octave', 'orbix.shape'))
class Offset:
    """Relative change added to the current value instead of replacing it."""
    __slots__ = ('delta',)

    def __init__(self, delta):
        self.delta = float(delta)

    def __repr__(self):
        return 'Offset(%+g)' % self.delta


class Step:
    """One-shot persistent change per press (like a manual edit), never restored."""
    __slots__ = ('delta',)

    def __init__(self, delta):
        self.delta = float(delta)

    def __repr__(self):
        return 'Step(%+g)' % self.delta


class Set:
    """One-shot persistent assignment per press (used with Step effects)."""
    __slots__ = ('value',)

    def __init__(self, value):
        self.value = float(value)

    def __repr__(self):
        return 'Set(%g)' % self.value


# These are reversible presets of existing engine parameters, not new DSP.
# Absolute values: the most recently activated button wins. Offset values are
# relative and add up (Octave Up + Pitch Drop = no change).
# Freeze is the native Motion Hold fragment texture, not a spectral freeze.
BUTTON_EFFECTS = {
    'Freeze': {'grain.enabled': 1, 'motion.enabled': 1, 'motion.hold': 1},
    'Reverse': {'motion.enabled': 1, 'motion.reverse': 1},
    'Delay Throw': {'delay.mix': .65, 'delay.feedback': .6},
    'Reverb Wash': {'reverb.mix': .85, 'reverb.size': .95, 'reverb.decay': 12},
    'Pitch Drop': {'grain.enabled': 1, 'grain.pitch': Offset(-12)},
    'Bypass': {'delay.mix': 0, 'reverb.mix': 0, 'shimmer.mix': 0,
               'tape.enabled': 0, 'comp.enabled': 0,
               **{key: 0 for key in ('eq.low', 'eq.lmid', 'eq.mid',
                                     'eq.hmid', 'eq.high', 'eq.air')}},
    'ORBIX': {'orbix.enabled': 1},
    'Octave Up': {'grain.enabled': 1, 'grain.pitch': Offset(12)},
    'Shimmer Burst': {'shimmer.mix': .8, 'shimmer.feedback': .7},
    'Grain Burst': {'grain.enabled': 1, 'grain.density': 32, 'grain.spray': .6},
    'Lo-Fi': {'tape.enabled': 1, 'tape.bit8': 1},
    'Stutter': {'motion.enabled': 1, 'motion.jump': 1, 'motion.chaos': 1},
    # Step actions: every press transposes by one octave and stays there.
    'Octave +': {'grain.enabled': Set(1), 'grain.pitch': Step(12)},
    'Octave -': {'grain.enabled': Set(1), 'grain.pitch': Step(-12)},
}
STEP_EFFECTS = frozenset(name for name, preset in BUTTON_EFFECTS.items()
                         if any(isinstance(v, (Step, Set)) for v in preset.values()))
# (left X/Y, right X/Y, (L2, R2, L3, R3), sensitivity %, smoothing ms).
# Presets affect assignments only, never DSP values or transport.
# L2/R2 are Hold (press-and-hold gestures); L3/R3 are Toggle because a stick
# click is awkward to keep pressed while moving the same stick.
FACTORY_PRESETS = {
    'Granular': (('grain.position', 'grain.size'), ('grain.pitch', 'grain.density'),
                 ('Freeze', 'Reverse', 'Octave -', 'Octave +'), 70, 60),
    'Ambient': (('grain.position', 'grain.spray'), ('reverb.mix', 'shimmer.mix'),
                ('Freeze', 'Reverb Wash', 'Shimmer Burst', 'Bypass'), 50, 180),
    'Texture': (('grain.size', 'grain.spray'), ('grain.density', 'roam.speed'),
                ('Grain Burst', 'Freeze', 'Reverse', 'Stutter'), 60, 90),
    'Echo': (('delay.time', 'delay.feedback'), ('delay.mix', 'reverb.mix'),
             ('Delay Throw', 'Reverb Wash', 'Freeze', 'Bypass'), 50, 100),
    'Tape': (('tape.saturation', 'tape.wow'), ('grain.pitch', 'tape.flutter'),
             ('Pitch Drop', 'Lo-Fi', 'Reverse', 'Bypass'), 40, 140),
    'ORBIX Play': (('orbix.rotation', 'orbix.gravity'), ('orbix.bounce', 'orbix.reverb'),
                   ('ORBIX', 'Reverb Wash', 'Freeze', 'Shimmer Burst'), 50, 120),
}

def defaults():
    sticks = {}
    for name, axes in (('left_stick', (0, 1)), ('right_stick', (2, 3))):
        sticks[name] = dict(enabled=False, x=None, y=None, deadzone=12,
                            sensitivity=100, invert_x=False, invert_y=False,
                            mode='Spring', smoothing=60, axis_x=axes[0], axis_y=axes[1])
    return dict(version=VERSION, **sticks,
                l2=dict(enabled=False, effect=None, mode='Hold'),
                r2=dict(enabled=False, effect=None, mode='Hold'),
                l3=dict(enabled=False, effect=None, mode='Toggle'),
                r3=dict(enabled=False, effect=None, mode='Toggle'))


def factory_preset(name, current):
    left, right, buttons, sensitivity, smoothing = FACTORY_PRESETS[name]
    result = defaults()
    for key, axes in (('left_stick', left), ('right_stick', right)):
        result[key].update(enabled=True, x=axes[0], y=axes[1],
                           sensitivity=sensitivity, smoothing=smoothing)
        # Device calibration/preferences are not a musical preset.
        for field in ('axis_x', 'axis_y', 'deadzone', 'invert_x', 'invert_y'):
            result[key][field] = current[key][field]
    for key, effect in zip(BUTTONS, buttons):
        result[key].update(enabled=effect is not None, effect=effect,
                           mode='Toggle' if effect == 'ORBIX' or key in ('l3', 'r3') else 'Hold')
    return result


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
                dst[key] = v if isinstance(v, str) and v in AXIS_IDS else None
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
        self.user_preset = None
        try:
            raw = self._read().get(CONFIG_KEY)
            self.data = validate(raw)
            user = raw.get('user_preset') if isinstance(raw, dict) else None
            if (isinstance(user, dict) and user.get('version') == VERSION
                    and all(isinstance(user.get(name), dict) for name in LEGACY_CONTROLS)):
                self.user_preset = validate(user)
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
            obj[CONFIG_KEY] = dict(self.data, user_preset=self.user_preset)
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

    def replace_controls(self, data, user=None, replace_user=False):
        """Commit a preset atomically; a failed save keeps both old states."""
        old_data, old_user = self.data, self.user_preset
        self.data = validate(data)
        if replace_user:
            self.user_preset = validate(user)
        if self.save():
            return True
        self.data, self.user_preset = old_data, old_user
        return False

    def save_user(self):
        return self.replace_controls(self.data, self.data, replace_user=True)

    def load_user(self):
        return self.user_preset is not None and self.replace_controls(self.user_preset)

    def apply_factory(self, name):
        # The first factory preset archives the existing setup, including a
        # migrated pre-preset installation, without overwriting a saved slot.
        return self.replace_controls(factory_preset(name, self.data), self.data,
                                     replace_user=self.user_preset is None)


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
        self.activated = {}  # button control -> activation sequence number
        self.sequence = 0
        self.offsets = {}    # parameter -> total relative change applied now
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

    def supports_preset(self, data):
        axes = (data[name][axis] for name in ('left_stick', 'right_stick') for axis in ('x', 'y'))
        effects = (data[name]['effect'] for name in BUTTONS)
        return (all(key is None or key in AXIS_IDS and self.bounds(key) for key in axes)
                and all(effect is None or effect in BUTTON_EFFECTS
                        and all(self.bounds(key) for key in BUTTON_EFFECTS[effect]) for effect in effects))

    def _external_changes(self):
        for key, previous in self.written.items():
            value = self.bus.get(key)
            if abs(value - previous) > 1e-8:
                self.base[key] = value

    def _ordered_sources(self):
        # Sticks first (continuous), then buttons in activation order so the
        # most recently pressed effect wins a conflict on the same parameter.
        sticks = [name + '.' + axis for name in CONTROLS if name.endswith('stick') for axis in ('x', 'y')]
        buttons = sorted((name for name in BUTTONS if name in self.sources),
                         key=lambda name: self.activated.get(name, 0))
        return sticks + buttons

    def _apply(self):
        combined, offsets = {}, {}
        for source in self._ordered_sources():
            for key, value in self.sources.get(source, {}).items():
                if isinstance(value, Offset):
                    offsets[key] = offsets.get(key, 0.0) + value.delta
                else:
                    combined[key] = value
        touched = set(combined) | set(offsets)
        for key in touched:
            self.base.setdefault(key, self.bus.get(key))
        self.offsets = offsets
        for key in set(self.written) | touched:
            if key in touched:
                target = combined.get(key, self.base[key]) + offsets.get(key, 0.0)
            else:
                target = self.base.get(key, self.bus.get(key))
            bounds = self.bounds(key)
            if bounds:
                target = max(bounds[0], min(bounds[1], target))
            if key in DISCRETE_PARAMETERS and key in touched:
                target = float(round(target))
            if abs(self.bus.get(key) - target) > 1e-8:
                self.bus.set(key, target)
            if key in touched:
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

    def release_transient(self):
        """Leaving the sound tabs: release sticks and Hold buttons.

        Toggle effects stay on across tab changes until toggled off, the
        Advanced Settings menu opens, or the app exits (full cancel()).
        """
        self._external_changes()
        for control in CONTROLS:
            if control in self.toggled:
                continue
            for source in (control, control + '.x', control + '.y'):
                self.sources.pop(source, None)
                self.gestures.pop(source, None)
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
        if cfg['effect'] in STEP_EFFECTS:
            self._step(BUTTON_EFFECTS[cfg['effect']])
            return
        if cfg['mode'] == 'Toggle' and name in self.toggled:
            self.toggled.remove(name)
            self.sources.pop(name, None)
        elif cfg['effect'] is not None:
            self.sources[name] = dict(BUTTON_EFFECTS[cfg['effect']])
            self.sequence += 1
            self.activated[name] = self.sequence
            if cfg['mode'] == 'Toggle':
                self.toggled.add(name)
        self._apply()

    def _step(self, preset):
        """Apply a persistent edit; an active override keeps working on top."""
        for key, change in preset.items():
            bounds = self.bounds(key)
            if key in self.written:
                current = self.base[key]
            else:
                current = self.bus.get(key)
            value = change.value if isinstance(change, Set) else current + change.delta
            if bounds:
                value = max(bounds[0], min(bounds[1], value))
            if key in self.written:
                self.base[key] = value
            elif abs(self.bus.get(key) - value) > 1e-8:
                self.bus.set(key, value)
        self._apply()

    def tick(self, axes, now, performance=True, excluded_axes=()):
        self._external_changes()
        dt = 1 / 60 if self.last_time is None else max(0, min(.1, now - self.last_time))
        self.last_time = now
        if not performance:
            self.release_transient()
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
                    # Start from the value without relative button effects so
                    # an active Octave Up/Pitch Drop is not applied twice.
                    current = self.bus.get(key) - self.offsets.get(key, 0.0)
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
    LABELS = dict(left_stick='Left Stick', right_stick='Right Stick', l2='L2 Button', r2='R2 Button',
                  l3='L3 Click', r3='R3 Click')

    def __init__(self, settings, controls):
        self.settings, self.controls = settings, controls
        self.page = None
        self.index = 0
        self.parent_index = 0
        self.confirm = False
        self.pending = None
        self.return_index = 0

    def open(self):
        self.controls.cancel()
        self.page, self.index, self.confirm, self.pending = 'root', 0, False, None

    def rows(self):
        if self.confirm:
            key, label = ('restore', 'Restore Defaults') if self.pending is None else {
                'factory': ('apply_preset', 'Apply Preset'),
                'save_user': ('save_user', 'Save User'),
                'load_user': ('load_user', 'Load User'),
            }[self.pending[0]]
            return [('cancel', 'Cancel', ''), (key, label, '')]
        if self.page == 'root':
            return [(name, label, 'ON' if self.settings.data[name]['enabled'] else 'OFF')
                    for name, label in self.LABELS.items()] + [('presets', 'Presets', '>'),
                    ('reset', 'Reset to Defaults', '>'), ('back', 'Back', '')]
        if self.page == 'presets':
            user_state = ('Empty' if self.settings.user_preset is None else 'Saved'
                          if self.controls.supports_preset(self.settings.user_preset) else 'Unavailable')
            return [(name, name, '>' if self.controls.supports_preset(factory_preset(name, self.settings.data))
                     else 'Unavailable') for name in FACTORY_PRESETS] + [
                ('load_user', 'Load User', user_state),
                ('save_user', 'Save User', '>'), ('back', 'Back', '')]
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
            mode = 'Step' if cfg['effect'] in STEP_EFFECTS else cfg['mode']
            result += [('effect', 'Effect', effect), ('mode', 'Mode', mode)]
        return result + [('back', 'Back', '')]

    def back(self):
        if self.confirm:
            self.confirm = False
            self.index = self.return_index if self.pending is not None else len(self.LABELS) + 1
            self.pending = None
        elif self.page.endswith('.options'):
            self.page, self.index = self.page.split('.')[0], 3
        elif self.page != 'root':
            self.page, self.index = 'root', self.parent_index
        else:
            self.page, self.index = None, 0

    def handle(self, action):
        if self.page is None:
            return False
        # GRAINBERNIK_NAV_FIX_V3_20261106: B decreases editable values, A increases.
        if action in ('MENU', 'REBIND_CANCEL', 'TAB_PREV'):
            self.back()
            return True
        if action == 'B':
            # On navigation rows B still means Back / Cancel.
            key = self.rows()[self.index][0]
            if (not self.confirm and self.page not in ('root', 'presets')
                    and key not in ('back', 'options')):
                action = 'LEFT'
            else:
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
                    self.settings.replace_controls(defaults())
                elif key != 'cancel':
                    self.controls.cancel()
                    if self.pending[0] == 'factory':
                        self.settings.apply_factory(self.pending[1])
                    elif self.pending[0] == 'save_user':
                        self.settings.save_user()
                    else:
                        self.settings.load_user()
                self.back()
            return True
        if key == 'back':
            self.back()
        elif self.page == 'root':
            if key == 'reset':
                self.confirm, self.index, self.pending = True, 0, None
            else:
                self.parent_index = self.index
                self.page, self.index = key, 0
        elif self.page == 'presets':
            if key == 'load_user' and (self.settings.user_preset is None
                                       or not self.controls.supports_preset(self.settings.user_preset)):
                return True
            if key in FACTORY_PRESETS and not self.controls.supports_preset(factory_preset(key, self.settings.data)):
                return True
            self.return_index = self.index
            self.pending = ('factory', key) if key in FACTORY_PRESETS else (key, None)
            self.confirm, self.index = True, 0
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
