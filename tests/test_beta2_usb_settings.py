"""BETA 2.0 port, step 2: iPhone / USB audio page and engine hooks.

Needs the official BETA 2.0 package (pure-Python audio modules are imported):

    GRAINBRICK_BETA2_ZIP=/path/to/GrainBrick_BETA_2_0.zip

pygame and the settings classes are replaced by small fakes; no audio device,
ARM64 module or real display is used.
"""
import copy
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import types
import unittest
import zipfile
from unittest.mock import patch

REPO = Path(__file__).resolve().parents[1]
SHARED = REPO / 'rg40xx-h-patch' / 'grainbrick-beta'
BETA2 = REPO / 'rg40xx-h-patch' / 'grainbrick-beta2'
ZIP = os.environ.get('GRAINBRICK_BETA2_ZIP')
NAMES = ('pygame', 'pygame.draw', 'engine', 'engine.audio_inputs', 'engine.audio_devices',
         'engine.usb_capture_select_fx28', 'engine.control', 'engine.input', 'ui', 'ui.renderer',
         'gb_usb_settings', 'gb_usb_audio', 'gb_usb_gadget', 'gb_pipewire', 'gb_settings_rows')


class FakeControl:
    SETTINGS_PARAMS = ['settings.info_language', 'settings.audio_output', 'settings.ble_midi']

    def __init__(self, parameters=None):
        self.current_tab, self.settings_param_index, self.console_edit = 'SETTINGS', 0, True
        self.handled = []

    @property
    def current_param(self):
        return self.SETTINGS_PARAMS[self.settings_param_index] if self.current_tab == 'SETTINGS' else None

    def handle(self, action, value=None):
        self.handled.append(action)


class FakeInput:
    def poll(self, *a, **k):
        return [('A', None)]

    def close(self):
        pass


class FakeUI:
    VERY_DIM = DIM = ACCENT = WHITE = (1, 1, 1)
    screen = None

    def __init__(self):
        self.audio_output_id, self._audio_outputs_last_scan = 'internal', 0
        self.calls, self.info_language, self.saved_ids = [], 'EN', []

    def refresh_audio_outputs(self):
        self.calls.append('refresh')

    def draw_settings_page(self, controls):
        self.calls.append('native')

    def _save_settings(self):
        self.saved_ids.append(self.audio_output_id)

    def _gb_draw_footer(self, controls, worker):
        self.calls.append('native_footer')

    def draw_info_window(self, param, **kw):
        self.calls.append('info:' + param)
        # like the native renderer: looks the text up through the module global
        self.last_info = sys.modules['ui.renderer'].get_context_info(param, self.info_language)

    def text(self, *a, **k):
        self.calls.append('text:' + str(a[0]))

    def draw_bar_items(self, *a, **k):
        self.calls.append('bar')


@unittest.skipUnless(ZIP and Path(ZIP).is_file(), 'GRAINBRICK_BETA2_ZIP not set')
class Beta2USBSettings(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.tmp.name)
        with zipfile.ZipFile(ZIP) as archive:
            archive.extractall(cls.root / 'official')
        cls.app = cls.root / 'official' / 'grainbrick-beta2'

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def setUp(self):
        self.saved = {n: sys.modules.get(n) for n in NAMES}
        self.popen = subprocess.Popen
        self.path = list(sys.path)
        for name in NAMES:
            sys.modules.pop(name, None)
        pg = types.ModuleType('pygame')
        pg.init = lambda *a, **k: None
        pg.draw = types.SimpleNamespace(line=lambda *a, **k: None, rect=lambda *a, **k: None)
        sys.modules['pygame'] = pg
        sys.path[:0] = [str(self.app), str(BETA2), str(SHARED)]
        import gb_usb_audio
        gb_usb_audio.CONFIG = self.root / ('usb-%d.json' % id(self))
        self.audio = gb_usb_audio
        self.audio.Settings().save(dict(self.audio.DEFAULT, mode=self.audio.MODES[2]))
        import engine.audio_inputs, engine.audio_devices, engine.usb_capture_select_fx28  # noqa
        control, inputs, renderer = (types.ModuleType(n) for n in ('engine.control', 'engine.input', 'ui.renderer'))
        control.ControlManager, inputs.InputManager = type('ControlManager', (FakeControl,), {}), type('InputManager', (FakeInput,), {})
        renderer.UIEngine = type('UIEngine', (FakeUI,), {})
        self.titles = []
        renderer.get_context_info = lambda param, language='EN', *a: ('NATIVE', param)
        sys.modules.update({'engine.control': control, 'engine.input': inputs, 'ui.renderer': renderer})
        self.control, self.renderer = control, renderer

    def tearDown(self):
        subprocess.Popen = self.popen
        sys.path[:] = self.path
        for name, module in self.saved.items():
            if module is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = module

    def fake_route(self):
        card = {'number': 7, 'id': 'UAC2Gadget', 'gadget': True}
        route = {'card': card, 'capture': {'device': 2, 'pcm': 'plughw:CARD=UAC2Gadget,DEV=2'},
                 'playback': {'device': 3, 'pcm': 'plughw:CARD=UAC2Gadget,DEV=3'}}
        return patch.multiple(self.audio, connected=lambda system: True, endpoints=lambda s, c: route)

    def test_capture_route_keeps_pipewire_target_for_the_gadget(self):
        import engine.usb_capture_select_fx28 as fx28
        native = fx28.create_capture_route
        with self.fake_route(), patch.object(self.audio.gb_pipewire, 'available', return_value=True), \
                patch.object(self.audio.gb_pipewire, 'capture_pcm', return_value='pipewire:NODE=alsa_input.uac2'):
            self.assertTrue(self.audio.install_engine_hooks(settings_path=self.audio.CONFIG))
            choices = fx28.discover_usb_choices(str(self.root / 'missing-asound'))
            self.assertEqual(len(choices), 1)  # no MONO / other channel pairs for the gadget
            self.assertEqual(choices[0]['channel_label'], 'STEREO CH 1/2')
            self.assertEqual(choices[0]['device_label'], 'iPhone USB Gadget')
            pcm, config = fx28.create_capture_route(choices[0])
            self.assertEqual((pcm, config), ('pipewire:NODE=alsa_input.uac2', None))
        self.assertIsNot(fx28.create_capture_route, native)

    def test_native_route_for_other_devices_is_unchanged(self):
        import engine.usb_capture_select_fx28 as fx28
        with self.fake_route():
            self.audio.install_engine_hooks(settings_path=self.audio.CONFIG)
        pcm, config = fx28.create_capture_route({'first_channel': 0, 'channels': 2, 'hw_channels': 2,
                                                 'card_id': 'ZoomH1n', 'device_number': 0,
                                                 'device_pcm': 'plughw:CARD=ZoomH1n,DEV=0'})
        self.assertEqual((pcm, config), ('plughw:CARD=ZoomH1n,DEV=0', None))
        pcm, config = fx28.create_capture_route({'first_channel': 0, 'channels': 2, 'hw_channels': 2,
                                                 'card_id': 'UAC2Gadget', 'device_number': 2,
                                                 'device_pcm': 'pipewire:NODE=alsa_input.uac2'})
        self.assertEqual((pcm, config), ('pipewire:NODE=alsa_input.uac2', None))

    def test_record_worker_is_guarded_and_blocked_when_usb_is_gone(self):
        script = self.root / 'gb_usb_record_fx35.py'
        script.write_text('import sys; sys.exit(0)\n')
        with self.fake_route():
            self.audio.install_engine_hooks(settings_path=self.audio.CONFIG)
            process = subprocess.Popen([sys.executable, str(script), '--device',
                                        'pipewire:NODE=alsa_input.uac2'])
            process.wait()
            self.assertEqual(process.returncode, 0)
        with patch.object(self.audio, 'connected', lambda system: False):
            with self.assertRaises(OSError):
                subprocess.Popen([sys.executable, str(script), '--device', 'pipewire:NODE=alsa_input.uac2'])
            # Other devices (e.g. Zoom H1n) are never blocked.
            other = subprocess.Popen([sys.executable, str(script), '--device', 'plughw:CARD=ZoomH1n,DEV=0'])
            other.wait()
            self.assertEqual(other.returncode, 0)

    def attach(self):
        import gb_usb_settings as page
        with self.fake_route():
            self.assertTrue(page._attach())
        controls = self.control.ControlManager()
        ui = self.renderer.UIEngine()
        page._runtime.ui = ui
        return page, controls, ui

    def test_settings_row_and_key_are_added_last_and_aligned(self):
        page, controls, ui = self.attach()
        ui.gb_extra_settings_rows = lambda c: [('settings.ble_midi', 'BLUETOOTH MIDI', '>')]
        self.assertNotIn(page.PARAM, self.control.ControlManager.SETTINGS_PARAMS)  # lazily, after other layers
        ui.draw_settings_page(controls)
        keys = self.control.ControlManager.SETTINGS_PARAMS
        rows = ui.gb_extra_settings_rows(controls)
        self.assertEqual(keys[-1], page.PARAM)
        self.assertEqual([r[0] for r in rows], ['settings.ble_midi', page.PARAM])
        ui.draw_settings_page(controls)  # idempotent
        self.assertEqual(keys.count(page.PARAM), 1)
        self.assertEqual(len(ui.gb_extra_settings_rows(controls)), 2)

    def open_page(self):
        page, controls, ui = self.attach()
        ui.draw_settings_page(controls)
        controls.settings_param_index = self.control.ControlManager.SETTINGS_PARAMS.index(page.PARAM)
        controls.handle('A')
        return page, controls, ui

    def mode(self, page):
        return page._runtime.settings.data['mode']

    def test_a_opens_the_page_and_b_closes_it(self):
        page, controls, ui = self.open_page()
        self.assertTrue(page._runtime.open)
        self.assertEqual(controls.handled, [])           # consumed here
        self.assertFalse(controls.console_edit)
        ui.calls.clear()
        ui.draw_settings_page(controls)
        self.assertIn('info:' + page.PARAM, ui.calls)
        self.assertNotIn('native', ui.calls)
        controls.handle('B')
        self.assertFalse(page._runtime.open)
        controls.handle('LEFT')                           # delegated to the original handler
        self.assertEqual(controls.handled, ['LEFT'])

    def test_left_right_do_nothing_until_a_starts_editing(self):
        page, controls, ui = self.open_page()
        before = self.mode(page)
        controls.handle('RIGHT')
        controls.handle('LEFT')
        self.assertEqual(self.mode(page), before)
        controls.handle('A')                              # edit MODE
        self.assertTrue(page._runtime.edit)
        controls.handle('RIGHT')
        self.assertEqual(self.mode(page), self.audio.MODES[0])   # iPhone -> next, wraps to Disabled
        controls.handle('DOWN')                           # focus stays on the field
        self.assertEqual(page._runtime.index, 0)
        controls.handle('B')                              # B ends the edit, page stays
        self.assertFalse(page._runtime.edit)
        self.assertTrue(page._runtime.open)
        controls.handle('B')
        self.assertFalse(page._runtime.open)

    def test_hold_a_and_dpad_changes_at_once_without_editing(self):
        page, controls, ui = self.open_page()
        controls.handle('ADJUST_RIGHT')
        self.assertEqual(self.mode(page), self.audio.MODES[0])
        controls.handle('ADJUST_LEFT')
        self.assertEqual(self.mode(page), self.audio.MODES[2])
        self.assertFalse(page._runtime.edit)

    def test_on_off_fields_toggle_on_a_and_set_by_adjust(self):
        page, controls, ui = self.open_page()
        controls.handle('DOWN')                           # SEND TO IPHONE
        data = page._runtime.settings.data
        self.assertTrue(data['output'])
        controls.handle('A')
        self.assertFalse(page._runtime.settings.data['output'])
        controls.handle('ADJUST_RIGHT')
        self.assertTrue(page._runtime.settings.data['output'])
        controls.handle('ADJUST_LEFT')
        self.assertFalse(page._runtime.settings.data['output'])
        self.assertFalse(page._runtime.edit)

    def test_back_row_closes_with_a(self):
        page, controls, ui = self.open_page()
        for _ in range(4):
            controls.handle('DOWN')                       # rows: MODE OUTPUT INPUT STATUS BACK
        controls.handle('A')
        self.assertFalse(page._runtime.open)

    def test_other_layers_still_see_other_settings_rows(self):
        page, controls, ui = self.attach()
        controls.settings_param_index = 0
        controls.handle('A')
        self.assertEqual(controls.handled, ['A'])
        self.assertFalse(page._runtime.open)

    def test_tab_change_closes_the_page_and_info_text_is_localized(self):
        page, controls, ui = self.attach()
        ui.draw_settings_page(controls)
        controls.settings_param_index = self.control.ControlManager.SETTINGS_PARAMS.index(page.PARAM)
        controls.handle('A')
        controls.handle('A')                              # editing MODE
        controls.current_tab = 'GRAIN'
        ui.draw_settings_page(controls)
        self.assertFalse(page._runtime.open)
        self.assertFalse(page._runtime.edit)
        native = self.renderer.get_context_info
        # ORBIX Rings / OSCILLATOR info layers replace the global after our attach.
        self.renderer.get_context_info = lambda p, language='EN', *a: native(p, language, *a)
        ui.info_language = 'RU'
        ui.draw_info_window(page.PARAM)
        title, text = ui.last_info
        self.assertEqual(title, page.LABEL)
        self.assertIn('IPHONE', text.upper())
        ui.draw_info_window('settings.audio_output')
        self.assertEqual(ui.last_info, ('NATIVE', 'settings.audio_output'))

    def test_transient_gadget_output_is_not_saved_to_native_settings(self):
        page, controls, ui = self.attach()
        ui.audio_output_id = 'grainbernik_usb_gadget'
        ui._save_settings()
        self.assertEqual(ui.saved_ids, ['internal'])
        self.assertEqual(ui.audio_output_id, 'grainbernik_usb_gadget')


if __name__ == '__main__':
    unittest.main()
