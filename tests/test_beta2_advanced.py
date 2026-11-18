"""BETA 2.0 port, step 3: STICKS & BUTTONS (Advanced Settings).

Needs the official BETA 2.0 package for the real ParameterBus definitions:

    GRAINBRICK_BETA2_ZIP=/path/to/GrainBrick_BETA_2_0.zip

pygame and the UI classes are small fakes; the real pure-Python parameter
modules run in a subprocess so every id used by the presets is verified.
"""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import types
import unittest
import zipfile

REPO = Path(__file__).resolve().parents[1]
BETA2 = REPO / 'rg40xx-h-patch' / 'grainbrick-beta2'
ZIP = os.environ.get('GRAINBRICK_BETA2_ZIP')
DUMP = '''
import json, sys
sys.path.insert(0, sys.argv[1])
import engine.parameters as p
for m in ('engine.grain2', 'engine.grain3', 'engine.osc_integration',
          'engine.orbix_res_integration', 'engine.tempo_app', 'engine.orbix_res_control',
          'engine.rhythm.app'):
    __import__(m)
bus = p.create_default_parameters()
print(json.dumps({k: [v.value, v.minimum, v.maximum] for k, v in bus.params.items()}))
'''
NAMES = ('pygame', 'engine', 'engine.control', 'engine.input', 'engine.autokey', 'ui', 'ui.renderer',
         'gb_advanced2', 'gb_advanced2_controls', 'gb_settings_rows', 'gb_usb_settings')


def load_core():
    sys.modules.pop('gb_advanced2_controls', None)
    sys.path.insert(0, str(BETA2))
    try:
        import gb_advanced2_controls as core
    finally:
        sys.path.remove(str(BETA2))
    return core


class FakeParam:
    def __init__(self, value, lo, hi):
        self.value, self.minimum, self.maximum = value, lo, hi


class FakeBus:
    def __init__(self, table):
        self.params = {k: FakeParam(*v) for k, v in table.items()}

    def get(self, key):
        return self.params[key].value

    def set(self, key, value):
        p = self.params[key]
        p.value = max(p.minimum, min(p.maximum, float(value)))


@unittest.skipUnless(ZIP and Path(ZIP).is_file(), 'GRAINBRICK_BETA2_ZIP not set')
class Beta2Advanced(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.tmp.name)
        with zipfile.ZipFile(ZIP) as archive:
            archive.extractall(cls.root / 'official')
        app = cls.root / 'official' / 'grainbrick-beta2'
        out = subprocess.run([sys.executable, '-c', DUMP, str(app)], cwd=str(cls.root), check=True,
                             capture_output=True, text=True)
        cls.table = json.loads(out.stdout.strip().splitlines()[-1])

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def setUp(self):
        self.core = load_core()
        self.bus = FakeBus(self.table)
        self.path = self.root / ('settings-%d.json' % id(self))
        self.settings = self.core.Settings(self.path)
        self.controls = self.core.Controls(self.bus, self.settings)
        self.menu = self.core.Menu(self.settings, self.controls)

    # --- parameter ids -----------------------------------------------------
    def test_every_axis_and_effect_parameter_exists_in_beta2(self):
        core = self.core
        missing = [k for k, _ in core.AXIS_PARAMETERS if k not in self.table]
        missing += [k for e in core.BUTTON_EFFECTS.values() for k in e if k not in self.table]
        self.assertEqual(missing, [])
        self.assertEqual(len(self.controls.axis_choices()), len(core.AXIS_PARAMETERS) + 1)
        self.assertEqual(self.controls.effect_choices()[1:], list(core.BUTTON_EFFECTS))

    def test_all_factory_presets_are_supported_and_cover_new_features(self):
        core = self.core
        for name in core.FACTORY_PRESETS:
            self.assertTrue(self.controls.supports_preset(core.factory_preset(name, self.settings.data)), name)
        for name in ('Rhythm', 'Rings', 'Oscillator', 'Live', 'Grain 2/3'):
            self.assertIn(name, core.FACTORY_PRESETS)
        used = {k for n in core.FACTORY_PRESETS for k in core.FACTORY_PRESETS[n][0] + core.FACTORY_PRESETS[n][1]}
        for n in core.FACTORY_PRESETS:
            for effect in core.FACTORY_PRESETS[n][2]:
                used.update(core.BUTTON_EFFECTS[effect])
        for prefix in ('orbix.res.', 'osc.', 'tempo.', 'level.input_db', 'grain.size_random'):
            self.assertTrue(any(k.startswith(prefix) for k in used), prefix)

    def test_native_values_stay_inside_engine_bounds(self):
        for key in ('orbix.res.structure', 'osc.drive', 'tempo.bpm', 'level.input_db'):
            lo, hi = self.controls.bounds(key)
            self.assertLess(lo, hi)

    # --- behaviour on the real parameter table --------------------------------
    def test_hold_effect_restores_and_offset_is_relative(self):
        cfg = self.settings.data['l2']
        cfg.update(enabled=True, effect='Slow Down', mode='Hold')
        self.bus.set('tempo.bpm', 100)
        self.controls.button('l2', True)
        self.assertEqual(self.bus.get('tempo.bpm'), 80)
        self.controls.button('l2', False)
        self.assertEqual(self.bus.get('tempo.bpm'), 100)

    def test_step_effect_is_persistent(self):
        self.settings.data['r3'].update(enabled=True, effect='Tempo +5', mode='Toggle')
        self.bus.set('tempo.bpm', 120)
        for _ in range(2):
            self.controls.button('r3', True)
            self.controls.button('r3', False)
        self.assertEqual(self.bus.get('tempo.bpm'), 130)

    def test_rings_hold_changes_three_values_and_restores(self):
        self.settings.data['l2'].update(enabled=True, effect='Rings Bloom', mode='Hold')
        before = {k: self.bus.get(k) for k in self.core.BUTTON_EFFECTS['Rings Bloom']}
        self.controls.button('l2', True)
        self.assertEqual(self.bus.get('orbix.res.damping'), 15)
        self.controls.button('l2', False)
        self.assertEqual({k: self.bus.get(k) for k in before}, before)

    def test_stick_drives_rings_structure_and_springs_back(self):
        cfg = self.settings.data['left_stick']
        cfg.update(enabled=True, x='orbix.res.structure', y=None, smoothing=0)
        start = self.bus.get('orbix.res.structure')
        self.controls.tick({0: 1.0, 1: 0.0}, 1.0)
        self.assertGreater(self.bus.get('orbix.res.structure'), start)
        self.controls.tick({0: 0.0, 1: 0.0}, 1.1)
        self.assertAlmostEqual(self.bus.get('orbix.res.structure'), start)

    def test_old_101_settings_with_unknown_ids_load_safely(self):
        self.path.write_text(json.dumps({'other': 1, 'grainbernik_advanced': {
            'version': 1, 'left_stick': {'enabled': True, 'x': 'filter.cutoff', 'y': 'grain.size'}}}))
        s = self.core.Settings(self.path)
        self.assertIsNone(s.data['left_stick']['x'])
        self.assertEqual(s.data['left_stick']['y'], 'grain.size')
        self.assertTrue(s.save())
        self.assertEqual(json.loads(self.path.read_text())['other'], 1)

    # --- Console Controls ------------------------------------------------------------
    def press(self, *actions):
        for a in actions:
            self.menu.handle(a)

    def test_console_controls_enter_edit_quick_and_back(self):
        m = self.menu
        m.open()
        self.press('DOWN', 'DOWN')                   # L2 button
        self.assertEqual(m.rows()[m.index][0], 'l2')
        self.press('A')                               # enter
        self.assertEqual(m.page, 'l2')
        self.press('A')                               # Enabled toggles at once
        self.assertTrue(self.settings.data['l2']['enabled'])
        self.press('DOWN', 'A')                       # Effect: A starts editing
        self.assertTrue(m.edit)
        first = self.settings.data['l2']['effect']
        self.press('RIGHT')
        self.assertNotEqual(self.settings.data['l2']['effect'], first)
        self.press('DOWN')                            # focus stays while editing
        self.assertEqual(m.rows()[m.index][0], 'effect')
        self.press('B')                               # B ends edit, stays on page
        self.assertFalse(m.edit)
        self.assertEqual(m.page, 'l2')
        before = self.settings.data['l2']['effect']
        self.press('ADJUST_RIGHT')                    # A held + RIGHT: quick change
        self.assertNotEqual(self.settings.data['l2']['effect'], before)
        self.assertFalse(m.edit)
        self.press('B')
        self.assertEqual(m.page, 'root')
        self.press('B')
        self.assertIsNone(m.page)

    def test_active_preset_is_shown_and_becomes_user_after_a_change(self):
        core, m = self.core, self.menu
        self.assertEqual(core.active_preset(self.settings.data), 'None')
        self.assertTrue(self.settings.apply_factory('Rings'))
        self.assertEqual(core.active_preset(self.settings.data), 'Rings')
        m.open()
        self.assertEqual(dict((r[0], r[2]) for r in m.rows())['presets'], 'Rings')
        m.page = 'presets'
        self.assertEqual(dict((r[0], r[2]) for r in m.rows())['Rings'], 'ACTIVE')
        self.settings.data['l2']['effect'] = 'Input Cut'     # any manual change
        self.assertEqual(core.active_preset(self.settings.data), 'User')
        self.assertEqual(dict((r[0], r[2]) for r in m.rows())['Rings'], '>')
        self.settings.save_user()
        self.assertEqual(dict((r[0], r[2]) for r in m.rows())['load_user'], 'ACTIVE')
        # calibration is not part of a preset
        self.settings.apply_factory('Live')
        self.settings.data['left_stick']['deadzone'] = 20
        self.assertEqual(core.active_preset(self.settings.data), 'Live')

    def test_left_right_do_not_change_values_outside_edit(self):
        m = self.menu
        m.open()
        self.press('DOWN', 'DOWN', 'A', 'DOWN')       # on l2 page, Effect row
        value = self.settings.data['l2']['effect']
        self.press('LEFT', 'RIGHT')
        self.assertEqual(self.settings.data['l2']['effect'], value)

    def test_preset_needs_confirmation_and_b_cancels(self):
        m = self.menu
        m.open()
        for _ in range(6):
            self.press('DOWN')
        self.assertEqual(m.rows()[m.index][0], 'presets')
        self.press('A')
        names = [r[0] for r in m.rows()]
        for expected in ('Rhythm', 'Rings', 'Oscillator', 'Live', 'Grain 2/3'):
            self.assertIn(expected, names)
        self.press('A')                               # first preset: confirm page
        self.assertTrue(m.confirm)
        self.press('B')
        self.assertFalse(m.confirm)
        self.assertFalse(self.settings.data['left_stick']['enabled'])
        index = names.index('Rings')
        while m.index != index:
            self.press('DOWN')
        self.press('A', 'DOWN', 'A')                  # Cancel -> Apply Preset
        self.assertTrue(self.settings.data['left_stick']['enabled'])
        self.assertEqual(self.settings.data['left_stick']['x'], 'orbix.res.structure')
        self.assertEqual(self.settings.data['l2']['effect'], 'Rings Bloom')
        self.assertEqual(self.settings.data['l3']['mode'], 'Toggle')


class FakeControl:
    SETTINGS_PARAMS = ['settings.info_language', 'settings.ble_midi']

    def __init__(self, parameters=None):
        self.parameters = parameters
        self.current_tab, self.settings_param_index, self.console_edit = 'GRAIN', 0, False
        self.handled = []

    @property
    def current_param(self):
        return self.SETTINGS_PARAMS[self.settings_param_index] if self.current_tab == 'SETTINGS' else None

    def handle(self, action, value=None):
        self.handled.append(action)


class FakeInput:
    capture_mode = False

    def __init__(self):
        self.auto_key = None
        self.joy = None

    def poll(self, *a, **k):
        return []

    def close(self):
        pass


class FakeAuto:
    def __init__(self):
        self.queue = []

    def events(self):
        out, self.queue = self.queue, []
        return out


class FakeUI:
    VERY_DIM = DIM = ACCENT = WHITE = (1, 1, 1)
    SETTINGS_PATH = None
    screen = None

    def __init__(self):
        self.info_language, self.calls, self.info_mode = 'EN', [], False

    def draw_settings_page(self, controls):
        self.calls.append('native')

    def _save_settings(self):
        self.calls.append('save')

    def _gb_draw_footer(self, controls, worker):
        self.calls.append('native_footer')

    def draw_info_window(self, param, **kw):
        self.calls.append('info:' + param)

    def text(self, *a, **k):
        self.calls.append('text:' + str(a[0]))

    def draw_bar_items(self, items, **kw):
        self.calls.append(('bar', [t for t, _ in items]))


@unittest.skipUnless(ZIP and Path(ZIP).is_file(), 'GRAINBRICK_BETA2_ZIP not set')
class Beta2AdvancedAdapter(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        Beta2Advanced.setUpClass.__func__(cls)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def setUp(self):
        self.saved = {n: sys.modules.get(n) for n in NAMES}
        self.path = list(sys.path)
        for name in NAMES:
            sys.modules.pop(name, None)
        pg = types.ModuleType('pygame')
        pg.init = lambda *a, **k: None
        pg.QUIT, pg.JOYBUTTONDOWN, pg.JOYBUTTONUP, pg.JOYHATMOTION = 256, 1539, 1540, 1538
        pg.error = RuntimeError
        pg.draw = types.SimpleNamespace(line=lambda *a, **k: None, rect=lambda *a, **k: None)
        sys.modules['pygame'] = pg
        sys.path[:0] = [str(BETA2)]
        control, inputs, autokey, renderer = (types.ModuleType(n) for n in
                                              ('engine.control', 'engine.input', 'engine.autokey', 'ui.renderer'))
        control.ControlManager = type('ControlManager', (FakeControl,), {})
        inputs.InputManager = type('InputManager', (FakeInput,), {})
        autokey.AutoKeyAdapter = type('AutoKeyAdapter', (FakeAuto,), {})
        renderer.UIEngine = type('UIEngine', (FakeUI,), {})
        renderer.UIEngine.SETTINGS_PATH = str(self.root / ('s-%d.json' % id(self)))
        renderer.get_context_info = lambda param, language='EN', *a: ('NATIVE', param)
        sys.modules.update({'engine.control': control, 'engine.input': inputs,
                            'engine.autokey': autokey, 'ui.renderer': renderer})
        self.m = dict(control=control, inputs=inputs, autokey=autokey, renderer=renderer)
        import gb_advanced2 as adv
        self.adv = adv
        self.assertTrue(adv._attach())
        self.bus = FakeBus(Beta2Advanced.table)
        self.controls = control.ControlManager(self.bus)
        self.ui = renderer.UIEngine()
        adv._runtime.ui = self.ui
        self.auto = autokey.AutoKeyAdapter()

    def tearDown(self):
        sys.path[:] = self.path
        for name, module in self.saved.items():
            if module is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = module

    def ev(self, button, down=True):
        pg = sys.modules['pygame']
        return types.SimpleNamespace(type=pg.JOYBUTTONDOWN if down else pg.JOYBUTTONUP, button=button)

    def test_l3_r3_events_are_consumed_only_while_enabled(self):
        rt = self.adv._runtime
        self.auto.queue = [self.ev(15), self.ev(5)]
        self.assertEqual([e.button for e in self.auto.events()], [15, 5])   # OFF: untouched
        rt.settings.data['l3'].update(enabled=True, effect='Freeze', mode='Toggle')
        self.auto.queue = [self.ev(15), self.ev(15, False), self.ev(5)]
        self.assertEqual([e.button for e in self.auto.events()], [5])       # claimed, A kept
        self.assertEqual(self.bus.get('motion.hold'), 1)

    def test_l2_only_on_sound_tabs_and_release_is_always_matched(self):
        rt = self.adv._runtime
        rt.settings.data['l2'].update(enabled=True, effect='Mute Out', mode='Hold')
        self.controls.current_tab = 'SETTINGS'
        self.auto.queue = [self.ev(10)]
        self.assertEqual(len(self.auto.events()), 1)          # settings screen: native
        self.controls.current_tab = 'GRAIN'
        self.auto.queue = [self.ev(10, False)]
        self.assertEqual(len(self.auto.events()), 1)          # unmatched UP is not swallowed
        self.auto.queue = [self.ev(10)]
        self.assertEqual(self.auto.events(), [])
        self.assertEqual(self.bus.get('level.master_db'), -60)
        self.controls.current_tab = 'SETTINGS'                 # tab changed while held
        self.auto.queue = [self.ev(10, False)]
        self.assertEqual(self.auto.events(), [])
        self.assertEqual(self.bus.get('level.master_db'), 0)

    def test_settings_row_registered_last_and_aligned_with_usb_page(self):
        reg = sys.modules['gb_settings_rows']
        C, ui = self.m['control'].ControlManager, self.ui
        ui.gb_extra_settings_rows = lambda c: [('settings.ble_midi', 'BLUETOOTH MIDI', '>')]
        reg.register(C, ui, 'settings.grainbernik_usb_audio', 'IPHONE / USB AUDIO', lambda: 'OFF')
        ui.draw_settings_page(self.controls)
        rows = ui.gb_extra_settings_rows(self.controls)
        self.assertEqual([r[0] for r in rows], ['settings.ble_midi', 'settings.grainbernik_usb_audio',
                                                self.adv.PARAM])
        self.assertEqual(list(C.SETTINGS_PARAMS[-3:]), [r[0] for r in rows])
        ui.draw_settings_page(self.controls)                    # idempotent
        self.assertEqual(len(ui.gb_extra_settings_rows(self.controls)), 3)

    def open_page(self):
        ui, c = self.ui, self.controls
        ui.draw_settings_page(c)
        c.current_tab = 'SETTINGS'
        c.settings_param_index = c.SETTINGS_PARAMS.index(self.adv.PARAM)
        c.console_edit = True
        c.handle('A')
        return c

    def test_a_opens_page_b_closes_and_native_handler_is_not_called(self):
        c = self.open_page()
        self.assertTrue(self.adv._runtime.open)
        self.assertFalse(c.console_edit)
        self.assertEqual(c.handled, [])
        for action in ('L', 'R', 'TAB_PREV', 'TAB_NEXT'):
            c.handle(action)
        self.assertTrue(self.adv._runtime.open)                # tab switching blocked
        c.handle('B')                                          # root: B closes the page
        self.assertFalse(self.adv._runtime.open)
        self.assertEqual(c.handled, [])

    def test_draw_and_footer_follow_console_controls(self):
        self.open_page()
        self.ui.calls.clear()
        self.ui.draw_settings_page(self.controls)
        self.assertIn('info:' + self.adv.PARAM, self.ui.calls)
        self.assertNotIn('native', self.ui.calls)
        self.ui._gb_draw_footer(self.controls, None)
        bar = [c for c in self.ui.calls if isinstance(c, tuple)][-1][1]
        self.assertEqual(bar, ['D-PAD NAV', 'A OPEN', 'B BACK'])
        info = self.m['renderer'].get_context_info(self.adv.PARAM, 'RU')
        self.assertEqual(info[0], 'STICKS & BUTTONS')

    def test_info_panel_has_english_and_russian_help_for_every_effect_and_preset(self):
        core = self.adv._core
        for key in list(core.BUTTON_EFFECTS) + list(core.FACTORY_PRESETS):
            self.assertIn(key, self.adv.HELP, key)
            self.assertTrue(all(self.adv.HELP[key]), key)

    def test_russian_help_is_translated_and_info_shows_active_preset(self):
        adv = self.adv
        for key in adv._core.FACTORY_PRESETS:
            en, ru = adv.HELP[key]
            self.assertNotEqual(en, ru, key)
            self.assertRegex(ru, '[А-Яа-я]', key)
        rt = adv._runtime
        title, text = rt.info('EN')
        self.assertTrue(text.startswith('PRESET: NONE. '), text)
        rt.settings.apply_factory('Rings')
        self.assertTrue(rt.info('EN')[1].startswith('PRESET: RINGS. '))
        self.assertTrue(rt.info('RU')[1].startswith('ПРЕСЕТ: RINGS. '))
        rt.settings.data['l2']['effect'] = 'Input Cut'
        self.assertTrue(rt.info('RU')[1].startswith('ПРЕСЕТ: СВОЙ. '))
        self.ui.info_language = 'RU'
        rt.menu.open()
        self.ui.calls.clear()
        rt.draw(self.ui)
        self.assertIn('text:ЛЕВЫЙ СТИК'.lower(), [c.lower() for c in self.ui.calls if isinstance(c, str)])
        self.assertEqual(rt.footer_items(self.ui)[1][0], 'A ОТКРЫТЬ')

    def test_native_save_does_not_drop_our_block(self):
        rt = self.adv._runtime
        rt.settings.data['l2'].update(enabled=True, effect='Scatter')
        self.assertTrue(rt.settings.save())
        path = Path(self.m['renderer'].UIEngine.SETTINGS_PATH)
        self.ui._save_settings()
        self.assertIn('grainbernik_advanced', json.loads(path.read_text()))


if __name__ == '__main__':
    unittest.main()
