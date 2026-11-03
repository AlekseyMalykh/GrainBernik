"""Optional integration against the user's *unmodified* official ARM64 module.

Run on ARM64 Python 3.12 (or qemu-aarch64) with Pygame and NumPy:
  GRAINBRICK_OFFICIAL_DIR=/path/to/official/grainbrick-beta \
  SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy \
  python3 -m unittest discover -s tests -p test_native_advanced.py -v

No proprietary binaries are included. All writes go to a temporary app root.
Screenshots at 640x480 can be requested with GRAINBERNIK_TEST_OUTPUT.
"""
import importlib
import json
import os
from pathlib import Path
import platform
import sys
import tempfile
import unittest

OFFICIAL = os.environ.get('GRAINBRICK_OFFICIAL_DIR')
SUPPORTED = bool(OFFICIAL and platform.machine().lower() in ('aarch64', 'arm64')
                 and sys.version_info[:2] == (3, 12))


class Joy:
    def __init__(self):
        self.axes = [0.0] * 4

    def init(self): pass
    def quit(self): pass
    def get_name(self): return 'Integration controller'
    def get_numaxes(self): return len(self.axes)
    def get_axis(self, index): return self.axes[index]


@unittest.skipUnless(SUPPORTED, 'requires the official ARM64 beta 1.0 and Python 3.12')
class NativeIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = tempfile.TemporaryDirectory(prefix='grainbernik-native-')
        cls.app = Path(cls.root.name)
        # Use original assets read-only. The module resolves all writable app
        # paths from GRAINBRICK_ROOT, which points to our disposable directory.
        for source in Path(OFFICIAL).iterdir():
            if source.suffix == '.so' or source.name in ('resources', 'libSoundTouch.so.1'):
                (cls.app / source.name).symlink_to(source)
        os.environ['GRAINBRICK_ROOT'] = str(cls.app)
        sys.path.insert(0, str(Path(OFFICIAL).resolve()))
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'rg40xx-h-patch/grainbrick-beta'))
        import pygame
        cls.pg = pygame

        class StopBootstrap(Exception): pass

        def stop():
            raise StopBootstrap()

        real_init = pygame.init
        pygame.init = stop
        cls.adapter = importlib.import_module('gb_advanced')
        cls.adapter.install()
        try:
            importlib.import_module('main')
        except StopBootstrap:
            pass
        finally:
            pygame.init = real_init
        if not cls.adapter._attached:
            raise AssertionError('launcher hook did not attach before native initialization')
        from engine.parameters import create_default_parameters
        from engine.control import ControlManager
        from engine.input import InputManager
        from ui.renderer import UIEngine
        cls.create_bus = staticmethod(create_default_parameters)
        cls.Control, cls.Input, cls.UI = ControlManager, InputManager, UIEngine
        cls.UI.SETTINGS_PATH = str(cls.app / 'settings.json')
        pygame.init()
        cls.old_count, cls.old_joy = pygame.joystick.get_count, pygame.joystick.Joystick
        pygame.joystick.get_count = lambda: 1

    @classmethod
    def tearDownClass(cls):
        cls.adapter._runtime.controls.cancel()
        cls.pg.joystick.get_count, cls.pg.joystick.Joystick = cls.old_count, cls.old_joy
        cls.pg.quit()
        cls.root.cleanup()

    def setUp(self):
        (self.app / 'settings.json').unlink(missing_ok=True)
        self.bus = self.create_bus()
        self.controller = self.Control(self.bus)
        self.ui = self.UI()
        self.runtime = self.adapter._runtime
        self.joy = Joy()
        self.pg.joystick.Joystick = lambda index: self.joy
        self.input = self.Input()
        self.pg.event.clear()

    def tearDown(self):
        self.runtime.controls.cancel()

    def poll(self):
        return self.input.poll()

    def button(self, button, down=True, dispatch=True):
        event = self.pg.event.Event(self.pg.JOYBUTTONDOWN if down else self.pg.JOYBUTTONUP,
                                   button=button, joy=0)
        self.pg.event.post(event)
        actions = self.poll()
        if dispatch:
            for action, value in actions:
                self.controller.handle(action, value)
        return actions

    def tap(self, button):
        result = self.button(button)
        self.button(button, False)
        return result

    def hat(self, value):
        for position in (value, (0, 0)):
            self.pg.event.post(self.pg.event.Event(self.pg.JOYHATMOTION, hat=0, value=position, joy=0))
            for action, magnitude in self.poll():
                self.controller.handle(action, magnitude)

    def tab(self, name):
        self.controller.tab_index = self.controller.TABS.index(name)

    def snapshot(self, name):
        if os.environ.get('GRAINBERNIK_TEST_OUTPUT'):
            out = Path(os.environ['GRAINBERNIK_TEST_OUTPUT'])
            out.mkdir(parents=True, exist_ok=True)
            self.ui.screen.fill(self.ui.BG)
            self.ui.draw(self.controller, self.bus, None, None)
            surf = self.pg.transform.smoothscale(self.ui.screen, (640, 480))
            self.pg.image.save(surf, str(out / (name + '.png')))

    def test_settings_navigation_uses_native_input_and_renderer(self):
        self.tab('SETTINGS')
        original = ['settings.info_language', 'settings.save_params_on_exit',
                    'settings.audio_output', 'settings.button_mapping', 'settings.reset_sound_params']
        self.assertEqual(self.controller.SETTINGS_PARAMS, original + [self.adapter.ADVANCED_PARAM])
        for _ in range(5): self.hat((0, -1))
        self.assertEqual(self.controller.current_param, self.adapter.ADVANCED_PARAM)
        self.snapshot('settings-entry')
        self.tap(5)  # physical A opens the new menu
        self.assertEqual(self.runtime.menu.page, 'root')
        self.snapshot('advanced-root')
        self.tap(5)
        self.assertEqual(self.runtime.menu.page, 'left_stick')
        self.tap(5)  # Enabled ON
        self.assertTrue(self.runtime.settings.data['left_stick']['enabled'])
        self.hat((0, -1))
        self.hat((1, 0))  # X: None -> first actual engine parameter
        self.assertEqual(self.runtime.settings.data['left_stick']['x'], 'grain.position')
        self.snapshot('advanced-stick')
        self.hat((0, -1)); self.hat((0, -1)); self.tap(5)
        self.assertEqual(self.runtime.menu.page, 'left_stick.options')
        for _ in range(7): self.hat((0, -1))
        self.snapshot('advanced-options-scrolled')
        self.tap(4)  # B back to stick, then root, then Settings
        self.tap(4); self.tap(4)
        self.assertIsNone(self.runtime.menu.page)
        self.assertEqual(self.controller.current_tab, 'SETTINGS')

    def test_native_settings_and_advanced_settings_survive_each_other(self):
        self.runtime.settings.data['r2'].update(enabled=True, effect='Freeze', mode='Toggle')
        self.runtime.settings.save()
        obj = json.loads((self.app / 'settings.json').read_text())
        obj['future_app_key'] = {'hello': 1}
        (self.app / 'settings.json').write_text(json.dumps(obj))
        self.ui.toggle_save_params_on_exit()
        loaded = self.adapter._core.Settings(self.app / 'settings.json')
        self.assertEqual(loaded.data, self.runtime.settings.data)
        self.assertEqual(json.loads((self.app / 'settings.json').read_text())['future_app_key'], {'hello': 1})

    def test_start_stops_and_restarts_from_every_advanced_page(self):
        import copy
        self.tab('SETTINGS')
        for page in ('root', 'presets', 'left_stick', 'right_stick', 'left_stick.options',
                     'right_stick.options', 'l2', 'r2'):
            with self.subTest(page=page):
                self.runtime.menu.open()
                self.runtime.menu.page, self.runtime.menu.index = page, 1
                settings_before = copy.deepcopy(self.runtime.settings.data)
                self.bus.set('transport.playing', 1)
                self.assertEqual(self.tap(13), [('START', 1)])
                self.assertEqual(self.bus.get('transport.playing'), 0)
                self.assertEqual((self.runtime.menu.page, self.runtime.menu.index), (page, 1))
                self.tap(13)
                self.assertEqual(self.bus.get('transport.playing'), 1)
                self.assertEqual(self.runtime.settings.data, settings_before)
        self.runtime.menu.open()
        self.runtime.menu.confirm = True
        self.bus.set('transport.playing', 1)
        self.tap(13)
        self.assertEqual(self.bus.get('transport.playing'), 0)
        self.assertTrue(self.runtime.menu.confirm)

    def test_shoulders_switch_tabs_from_every_advanced_page_and_keep_assignments(self):
        import copy
        self.runtime.settings.data['left_stick'].update(enabled=True, x='orbix.rotation', y='orbix.gravity')
        self.runtime.settings.data['r2'].update(enabled=True, effect='ORBIX', mode='Toggle')
        self.assertTrue(self.runtime.settings.save())
        expected = copy.deepcopy(self.runtime.settings.data)
        for page in ('root', 'presets', 'left_stick', 'right_stick', 'left_stick.options',
                     'right_stick.options', 'l2', 'r2'):
            for button, tab in ((8, 'VISUAL'), (9, 'SAVE'), (15, 'VISUAL'), (16, 'SAVE')):
                with self.subTest(page=page, button=button):
                    self.tab('SETTINGS')
                    self.controller.settings_param_index = len(self.controller.SETTINGS_PARAMS) - 1
                    self.runtime.menu.open()
                    self.runtime.menu.page = page
                    self.tap(button)
                    self.assertEqual(self.controller.current_tab, tab)
                    self.assertIsNone(self.runtime.menu.page)
                    self.assertEqual(self.runtime.settings.data, expected)
                    self.assertEqual(self.adapter._core.Settings(self.app / 'settings.json').data, expected)
                    self.controller.handle('TAB_NEXT' if button in (8, 15) else 'TAB_PREV')
                    self.assertEqual(self.controller.current_tab, 'SETTINGS')
                    self.tap(5)
                    self.assertEqual(self.runtime.menu.page, 'root')
        self.runtime.menu.confirm = True
        self.tap(9)
        self.assertEqual(self.controller.current_tab, 'SAVE')
        self.assertIsNone(self.runtime.menu.page)
        self.assertFalse(self.runtime.menu.confirm)
        self.assertEqual(self.runtime.settings.data, expected)

    def test_advanced_context_and_navigation_follow_native_help_language(self):
        self.tab('SETTINGS')
        self.controller.settings_param_index = len(self.controller.SETTINGS_PARAMS) - 1
        for language in ('EN', 'RU'):
            self.runtime.menu.page = None
            self.ui.set_info_language(language)
            self.assertEqual(self.ui.footer_hint('B / A CHANGE'),
                             self.adapter._localized(self.ui, self.adapter.MESSAGES, 'footer_open'))
            self.snapshot('advanced-entry-' + language.lower())
            self.runtime.menu.open()
            seen = []
            positions = []
            original_text = self.ui.text

            def text(message, *args, **kwargs):
                seen.append(message)
                positions.append((message, args[0], args[1]))
                return original_text(message, *args, **kwargs)

            self.ui.text = text
            try:
                for page, index in (('root', 0), ('left_stick.options', 4), ('r2', 1)):
                    self.runtime.menu.page, self.runtime.menu.index = page, index
                    self.runtime.settings.data['r2']['effect'] = 'ORBIX'
                    frame_start = len(positions)
                    self.runtime.draw(self.ui)
                    frame = positions[frame_start:]
                    help_lines = self.ui._wrap_info_text(self.runtime.help_text(self.ui), max_chars=64)
                    help_ys = [y for message, x, y in frame if message in help_lines]
                    row_ys = [y for message, x, y in frame if x == 64]
                    self.assertTrue(help_ys)
                    self.assertLess(max(help_ys), min(row_ys), 'Context help must be above the control list')
                    self.assertIn(self.runtime.help_text(self.ui),
                                  [pair[1 if language == 'RU' else 0] for pair in self.adapter.HELP.values()])
                    self.snapshot('advanced-help-' + language.lower())
                self.runtime.menu.confirm, self.runtime.menu.index = True, 0
                self.runtime.draw(self.ui)
                self.assertIn(self.adapter._localized(self.ui, self.adapter.MESSAGES, 'reset_title'), seen)
                self.snapshot('advanced-reset-' + language.lower())
            finally:
                self.ui.text = original_text
            self.assertIn(self.adapter._localized(self.ui, self.adapter.MESSAGES, 'transport'), seen)
            self.assertIn(self.adapter._localized(self.ui, self.adapter.MESSAGES, 'navigation'), seen)
            self.assertEqual(self.ui.footer_hint('B / A CHANGE'),
                             self.adapter._localized(self.ui, self.adapter.MESSAGES, 'footer_change'))
            for key, pair in self.adapter.HELP.items():
                self.assertLessEqual(len(self.ui._wrap_info_text(pair[language == 'RU'], max_chars=64)), 2,
                                     (key, language, pair[language == 'RU']))
            if language == 'RU':
                self.assertTrue(any('КРЕСТОВИНА' in msg for msg in seen))
            self.runtime.menu.confirm = False

    def test_disabled_buttons_keep_native_actions(self):
        self.tab('GRAIN')
        before = {k: p.value for k, p in self.bus.params.items()}
        for button, action in ((10, 'L2'), (11, 'R2')):
            self.assertEqual(self.button(button, dispatch=False), [(action, 1)])
            self.button(button, False, dispatch=False)
        self.joy.axes = [1, -1, 1, -1]
        self.poll()
        self.assertEqual({k: p.value for k, p in self.bus.params.items()}, before)

    def test_hold_toggle_and_menu_cancel_against_actual_parameter_bus(self):
        self.tab('GRAIN')
        self.runtime.settings.data['l2'].update(enabled=True, effect='Delay Throw')
        self.runtime.settings.data['r2'].update(enabled=True, effect='Reverb Wash', mode='Toggle')
        self.assertEqual(self.button(10), [])
        self.assertAlmostEqual(self.bus.get('delay.mix'), .65)
        self.button(10, False)
        self.assertEqual(self.bus.get('delay.mix'), 0)
        self.tap(11)
        self.assertAlmostEqual(self.bus.get('reverb.mix'), .85)
        self.tap(11)
        self.assertEqual(self.bus.get('reverb.mix'), 0)
        self.button(10)
        self.controller.handle('TAB_NEXT')
        self.controller.handle('TAB_NEXT')
        self.controller.handle('TAB_NEXT')
        self.controller.handle('TAB_NEXT')  # leaves performance tabs for Settings
        self.assertEqual(self.controller.current_tab, 'SETTINGS')
        self.assertEqual(self.bus.get('delay.mix'), 0)
        self.button(10, False)

    def test_rebinding_focus_loss_and_disconnect_unwind_effects(self):
        self.tab('GRAIN')
        self.runtime.settings.data['l2'].update(enabled=True, effect='Pitch Drop')
        self.input.capture_mode = True
        actions = self.button(10, dispatch=False)
        self.assertTrue(actions)  # capture receives the physical button
        self.assertEqual(self.bus.get('grain.pitch'), 0)
        self.button(10, False, dispatch=False)
        self.input.capture_mode = False
        self.button(10)
        self.assertEqual(self.bus.get('grain.pitch'), -12)
        self.pg.event.post(self.pg.event.Event(self.pg.WINDOWFOCUSLOST))
        self.poll()
        self.assertEqual(self.bus.get('grain.pitch'), 0)
        self.button(10, False)
        self.pg.event.post(self.pg.event.Event(self.pg.WINDOWFOCUSGAINED))
        self.poll()
        self.button(10)
        self.assertEqual(self.bus.get('grain.pitch'), -12)
        self.pg.event.post(self.pg.event.Event(self.pg.JOYDEVICEREMOVED, instance_id=0))
        self.poll()
        self.assertEqual(self.bus.get('grain.pitch'), 0)
        self.button(10, False)

    def test_exit_chord_restores_before_native_sound_state_save(self):
        self.tab('GRAIN')
        self.runtime.settings.data['l2'].update(enabled=True, effect='Delay Throw')
        self.button(10)
        self.assertAlmostEqual(self.bus.get('delay.mix'), .65)
        self.button(12, dispatch=False)
        actions = self.button(13, dispatch=False)
        self.assertIn(('EXIT', 1), actions)
        self.assertEqual(self.bus.get('delay.mix'), 0)

    def test_real_catalog_has_no_phantom_filter_pan_tape_speed(self):
        choices = dict(self.runtime.controls.axis_choices())
        self.assertIn('grain.pitch', choices)
        self.assertIn('delay.time', choices)
        self.assertNotIn('filter.cutoff', choices)
        self.assertNotIn('pan', choices)
        self.assertNotIn('tape.speed', choices)
        self.assertEqual(self.runtime.controls.effect_choices(),
                         [None, 'Freeze', 'Reverse', 'Delay Throw', 'Reverb Wash', 'Pitch Drop', 'Bypass', 'ORBIX'])

    def test_orbix_real_catalog_xy_and_integer_selections(self):
        choices = dict(self.runtime.controls.axis_choices())
        orbix = {key for key in choices if key and key.startswith('orbix.')}
        expected = {'orbix.gravity', 'orbix.rotation', 'orbix.bounce', 'orbix.volume',
                    'orbix.attack', 'orbix.release', 'orbix.reverb', 'orbix.balls',
                    'orbix.root', 'orbix.scale', 'orbix.instrument', 'orbix.octave', 'orbix.shape'}
        self.assertEqual(orbix, expected)
        self.tab('GRAIN')
        self.controller.orbix_view_active = True
        cfg = self.runtime.settings.data['left_stick']
        cfg.update(enabled=True, x='orbix.rotation', y='orbix.gravity', smoothing=0)
        before = {key: self.bus.get(key) for key in orbix}
        self.joy.axes = [1, -1, 0, 0]
        self.poll()
        self.assertEqual(self.bus.get('orbix.rotation'), 55)
        self.assertEqual(self.bus.get('orbix.gravity'), 0)
        self.assertEqual(self.bus.get('orbix.enabled'), 0)  # XY never silently starts ORBIX
        self.joy.axes = [0] * 4
        self.poll()
        for key in self.adapter._core.DISCRETE_PARAMETERS:
            cfg['x'], cfg['y'] = key, None
            self.joy.axes = [.61, 0, 0, 0]
            self.poll()
            self.assertEqual(self.bus.get(key), round(self.bus.get(key)))
            self.joy.axes = [0] * 4
            self.poll()
        self.assertEqual({key: self.bus.get(key) for key in orbix}, before)
        cfg['x'], cfg['y'] = 'orbix.rotation', 'orbix.gravity'
        self.tab('SETTINGS')
        self.runtime.menu.open()
        self.runtime.menu.page, self.runtime.menu.index = 'left_stick', 1
        self.snapshot('orbix-axis-assignments')

    def test_orbix_trigger_modes_restore_enable_and_preserve_transport(self):
        self.tab('GRAIN')
        cfg = self.runtime.settings.data['r2']
        cfg.update(enabled=True, effect='ORBIX')
        for initial in (0, 1):
            for mode in ('Hold', 'Toggle'):
                self.bus.set('orbix.enabled', initial)
                cfg['mode'] = mode
                self.assertEqual(self.button(11), [])
                self.assertEqual(self.bus.get('orbix.enabled'), 1)
                self.assertEqual(self.bus.get('transport.playing'), 0)
                self.button(11, False)
                if mode == 'Toggle':
                    self.assertEqual(self.bus.get('orbix.enabled'), 1)
                    self.tap(11)
                self.assertEqual(self.bus.get('orbix.enabled'), initial)
        self.tab('SETTINGS')
        self.runtime.menu.open()
        self.runtime.menu.page, self.runtime.menu.index = 'r2', 1
        self.snapshot('orbix-button-assignment')

    def test_orbix_assignment_generates_sound_in_native_dsp(self):
        import wave
        import numpy as np
        from engine.sample import SampleBuffer
        from engine.granular_c import GranularEngine
        from engine.dsp_chain import DSPChain
        path = self.app / 'orbix-silence.wav'
        with wave.open(str(path), 'wb') as out:
            out.setparams((2, 2, 48000, 0, 'NONE', 'not compressed'))
            out.writeframes(bytes(48000 * 4))
        chain = DSPChain(GranularEngine(SampleBuffer(str(path)), self.bus), self.bus)
        self.tab('GRAIN')
        self.bus.set('transport.playing', 1)
        self.bus.set('orbix.volume', 100)
        self.bus.set('orbix.balls', 12)
        self.bus.set('orbix.gravity', 420)
        self.runtime.settings.data['l2'].update(enabled=True, effect='ORBIX')
        self.button(10)
        peak = 0
        for _ in range(160):
            rendered = chain.render(1024)
            self.assertTrue(np.isfinite(rendered).all())
            peak = max(peak, float(np.abs(rendered).max()))
        self.assertGreater(peak, 1e-5, 'ORBIX did not generate audio from a silent input sample')
        self.button(10, False)
        self.assertEqual(self.bus.get('orbix.enabled'), 0)

    def test_live_xy_uses_actual_native_bounds_and_release(self):
        self.tab('GRAIN')
        self.runtime.settings.data['left_stick'].update(enabled=True, x='grain.position',
                                                        y='grain.size', smoothing=0)
        self.runtime.settings.data['right_stick'].update(enabled=True, x='delay.mix',
                                                         y='reverb.mix', smoothing=0, mode='Latch')
        before = {k: self.bus.get(k) for k in ('grain.position', 'grain.size', 'delay.mix', 'reverb.mix')}
        self.joy.axes = [1, -1, 1, 1]
        self.poll()
        self.assertEqual(self.bus.get('grain.position'), 1)
        self.assertEqual(self.bus.get('grain.size'), .02)
        self.assertEqual(self.bus.get('delay.mix'), .5)
        self.assertEqual(self.bus.get('reverb.mix'), .5)
        self.joy.axes = [0] * 4
        self.poll()
        self.assertEqual(self.bus.get('grain.position'), before['grain.position'])
        self.assertEqual(self.bus.get('grain.size'), before['grain.size'])
        self.assertEqual(self.bus.get('delay.mix'), .5)
        self.runtime.controls.cancel()
        self.assertEqual({k: self.bus.get(k) for k in before}, before)

    def test_effect_presets_render_through_original_dsp_and_restore(self):
        import math
        import struct
        import wave
        import numpy as np
        from engine.sample import SampleBuffer
        from engine.granular_c import GranularEngine
        from engine.dsp_chain import DSPChain
        path = self.app / 'test-signal.wav'
        samples = [int(8000 * math.sin(2 * math.pi * 220 * i / 48000)) for i in range(48000)]
        with wave.open(str(path), 'wb') as out:
            out.setparams((2, 2, 48000, 0, 'NONE', 'not compressed'))
            out.writeframes(b''.join(struct.pack('<hh', v, v) for v in samples))
        sample = SampleBuffer(str(path))
        granular = GranularEngine(sample, self.bus)
        chain = DSPChain(granular, self.bus)
        self.bus.set('transport.playing', 1)
        self.tab('GRAIN')
        self.runtime.settings.data['l2']['enabled'] = True
        for effect in self.runtime.controls.effect_choices()[1:]:
            with self.subTest(effect=effect):
                before = {k: p.value for k, p in self.bus.params.items()}
                self.runtime.settings.data['l2']['effect'] = effect
                self.button(10)
                for _ in range(3):
                    rendered = chain.render(256)
                    self.assertEqual(rendered.shape, (256, 2))
                    self.assertTrue(np.isfinite(rendered).all())
                self.button(10, False)
                self.assertEqual({k: p.value for k, p in self.bus.params.items()}, before)

    def preset_choice(self, key, confirm=True):
        menu = self.runtime.menu
        menu.page, menu.confirm = 'presets', False
        menu.index = [row[0] for row in menu.rows()].index(key)
        self.tap(5)
        if confirm and menu.confirm:
            self.hat((0, -1))
            self.tap(5)

    def test_factory_presets_via_native_input_keep_audio_calibration_and_archive_user(self):
        import copy
        self.tab('SETTINGS')
        self.runtime.settings.data['left_stick'].update(enabled=True, x='orbix.root', axis_x=3, axis_y=2)
        self.runtime.settings.save()
        before = copy.deepcopy(self.runtime.settings.data)
        audio = {key: p.value for key, p in self.bus.params.items()}
        self.runtime.menu.open()
        for _ in range(4): self.hat((0, -1))
        self.tap(5)
        self.assertEqual(self.runtime.menu.page, 'presets')
        for name in self.adapter._core.FACTORY_PRESETS:
            with self.subTest(preset=name):
                self.preset_choice(name)
                self.assertEqual(self.runtime.settings.data,
                                 self.adapter._core.factory_preset(name, before))
                self.assertEqual(self.runtime.settings.user_preset, before)
                self.assertEqual({key: p.value for key, p in self.bus.params.items()}, audio)
        for language in ('EN', 'RU'):
            self.ui.set_info_language(language)
            self.runtime.menu.page, self.runtime.menu.index = 'presets', 6
            self.snapshot('presets-list-' + language.lower())
            self.preset_choice('ORBIX Play', confirm=False)
            self.snapshot('presets-confirm-' + language.lower())
            self.tap(4)
        self.assertEqual(self.runtime.settings.user_preset, before)

    def test_user_slot_save_load_overwrite_and_native_settings_merge(self):
        import copy
        self.tab('SETTINGS')
        self.runtime.menu.open()
        self.preset_choice('Granular')
        original_slot = copy.deepcopy(self.runtime.settings.user_preset)
        self.preset_choice('save_user', confirm=False)
        self.tap(4)
        self.assertEqual(self.runtime.settings.user_preset, original_slot)
        self.preset_choice('save_user')
        user = copy.deepcopy(self.runtime.settings.data)
        self.preset_choice('Ambient')
        self.assertNotEqual(self.runtime.settings.data, user)
        self.preset_choice('load_user')
        self.assertEqual(self.runtime.settings.data, user)
        self.ui.toggle_save_params_on_exit()
        loaded = self.adapter._core.Settings(self.app / 'settings.json')
        self.assertEqual(loaded.user_preset, user)
        self.assertEqual(loaded.data, user)
        self.controller = self.Control(self.bus)
        self.assertEqual(self.adapter._runtime.settings.user_preset, user)
        self.assertEqual(self.adapter._runtime.settings.data, user)

    def test_pending_preset_keeps_transport_tabs_and_bilingual_help(self):
        import copy
        self.tab('SETTINGS')
        self.runtime.menu.open()
        before = copy.deepcopy(self.runtime.settings.data)
        for action in ('Granular', 'save_user'):
            self.preset_choice(action, confirm=False)
            self.bus.set('transport.playing', 1)
            self.tap(13)
            self.assertEqual(self.bus.get('transport.playing'), 0)
            self.assertTrue(self.runtime.menu.confirm)
            for language in ('EN', 'RU'):
                self.ui.set_info_language(language)
                self.snapshot('presets-' + action.lower() + '-' + language.lower())
            self.tap(9)
            self.assertEqual(self.controller.current_tab, 'SAVE')
            self.assertIsNone(self.runtime.menu.page)
            self.assertIsNone(self.runtime.menu.pending)
            self.assertEqual(self.runtime.settings.data, before)
            self.assertIsNone(self.runtime.settings.user_preset)
            self.tab('SETTINGS')
            self.runtime.menu.open()


if __name__ == '__main__':
    unittest.main()
