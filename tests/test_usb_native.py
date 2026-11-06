"""Optional real official GrainBrick 1.0.1 ARM64 integration. No real ALSA required.

Set GRAINBRICK_OFFICIAL_DIR; run under ARM64 Python 3.12 (including qemu).
All native/config writes are redirected into a temporary directory.
"""
import copy
import importlib
import os
from pathlib import Path
import platform
import sys
import tempfile
import unittest
from unittest.mock import patch

APP = Path(__file__).resolve().parents[1] / 'rg40xx-h-patch/grainbrick-beta'
sys.path.insert(0, str(APP))
OFFICIAL = os.environ.get('GRAINBRICK_OFFICIAL_DIR')
SUPPORTED = bool(OFFICIAL and platform.machine().lower() in ('aarch64', 'arm64')
                 and sys.version_info[:2] == (3, 12) and (Path(OFFICIAL) / '_vendor').is_dir())


@unittest.skipUnless(SUPPORTED, 'requires official 1.0.1 ARM64 module + Python 3.12')
class NativeUSB(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='grainbernik-usb-native-')
        cls.root = Path(cls.temp.name)
        official = Path(OFFICIAL).resolve()
        for source in official.iterdir():
            if source.suffix == '.so' or source.name in ('resources', 'libSoundTouch.so.1'):
                (cls.root / source.name).symlink_to(source)
        os.environ['GRAINBRICK_ROOT'] = str(cls.root)
        sys.path.insert(0, str(official))
        sys.path.insert(0, str(official / '_vendor'))
        import pygame
        import gb_usb_audio as audio
        import gb_usb_gadget as gadget
        cls.pg, cls.audio = pygame, audio
        audio.CONFIG = cls.root / 'gb_usb_audio.json'
        cls.system = gadget.System(cls.root / 'system', '4.9.fixture')
        cls.card_path = cls.system.path('/proc/asound/card7')
        cls.card_path.mkdir(parents=True)
        (cls.card_path / 'id').write_text('UAC2Gadget')
        (cls.card_path.parent / 'cards').write_text('7 [UAC2Gadget ]: UAC2Gadget - Gadget\n')
        for name in ('pcm2c', 'pcm3p'):
            path = cls.card_path / name / 'sub0'
            path.mkdir(parents=True)
            (path / 'status').write_text('closed')
        cls.udc = cls.system.path('/sys/class/udc/udc0/state')
        cls.udc.parent.mkdir(parents=True)
        cls.udc.write_text('configured')

        class Stop(Exception): pass
        old_init = pygame.init

        def stop():
            # Real engine and UI modules exist now. Attach with fixture system.
            audio.install_engine_hooks(system=cls.system)
            raise Stop()

        pygame.init = stop
        try:
            importlib.import_module('main')
        except Stop:
            pass
        finally:
            pygame.init = old_init
        cls.advanced = importlib.import_module('gb_advanced')
        cls.usb = importlib.import_module('gb_usb_settings')
        cls.advanced._attach()
        cls.usb._attach()
        from engine.parameters import create_default_parameters
        from engine.control import ControlManager
        from ui.renderer import UIEngine
        from engine import audio_inputs, audio_devices
        cls.inputs, cls.devices = audio_inputs, audio_devices
        cls.create_bus, cls.Control, cls.UI = staticmethod(create_default_parameters), ControlManager, UIEngine
        UIEngine.SETTINGS_PATH = str(cls.root / 'settings.json')
        pygame.init()

    @classmethod
    def tearDownClass(cls):
        cls.usb._runtime.close()
        cls.pg.quit()
        cls.temp.cleanup()

    def setUp(self):
        cfg = copy.deepcopy(self.audio.DEFAULT)
        self.audio.Settings().save(cfg)
        self.udc.write_text('configured')
        self.bus = self.create_bus()
        self.controller = self.Control(self.bus)
        self.ui = self.UI()
        self.runtime = self.usb._runtime
        self.runtime.monitor = self.audio.Monitor(self.system)
        self.runtime.last_scan = 0
        self.controller.tab_index = self.controller.TABS.index('SETTINGS')

    def enable(self):
        cfg = copy.deepcopy(self.runtime.settings.data)
        cfg['mode'] = self.audio.MODES[2]
        self.assertTrue(self.runtime.settings.save(cfg))
        self.runtime.last_scan = 0
        self.runtime.tick()

    def test_capture_schema_is_accepted_by_native_enumerator(self):
        self.enable()
        result = self.inputs.available_usb_captures()
        self.assertEqual(result[0]['pcm'], 'plughw:CARD=UAC2Gadget,DEV=2')
        self.assertEqual(result[0]['device_number'], 2)
        self.assertEqual(result[0]['card'], 7)

    def test_native_resolver_uses_gadget_output(self):
        self.enable()
        self.assertIn(('grainbernik_usb_gadget', 'USB GADGET', 'plughw:CARD=UAC2Gadget,DEV=3'),
                      self.devices.available_outputs())
        self.assertEqual(self.devices.resolve_output('grainbernik_usb_gadget'), 'plughw:CARD=UAC2Gadget,DEV=3')
        self.assertEqual(self.ui.audio_output_id, 'grainbernik_usb_gadget')

    def test_disable_and_unplug_restore_native_output(self):
        previous = self.ui.audio_output_id
        self.enable()
        self.udc.write_text('not attached')
        self.runtime.last_scan = 0
        self.runtime.tick()
        self.assertEqual(self.ui.audio_output_id, previous)
        self.assertEqual(self.inputs.available_usb_captures(), [])
        self.udc.write_text('configured')
        self.runtime.last_scan = 0
        self.runtime.tick()
        self.assertEqual(self.ui.audio_output_id, 'grainbernik_usb_gadget')
        cfg = copy.deepcopy(self.runtime.settings.data)
        cfg['mode'] = 'Disabled'
        self.runtime.settings.save(cfg)
        self.runtime.last_scan = 0
        self.runtime.tick()
        self.assertEqual(self.ui.audio_output_id, previous)

    def test_does_not_save_transient_output_in_native_config(self):
        import json
        self.enable()
        self.ui._save_settings()
        saved = json.loads((self.root / 'settings.json').read_text())
        self.assertNotIn('grainbernik_usb_gadget', str(saved))
        self.assertEqual(self.ui.audio_output_id, 'grainbernik_usb_gadget')

    def test_native_aplay_uses_direct_16bit_stereo_48k_pcm(self):
        from engine.audio import AudioOutput
        self.enable()
        output = AudioOutput(device=self.devices.resolve_output('grainbernik_usb_gadget'))
        argv = output._aplay_args()
        self.assertEqual(argv[argv.index('-D') + 1], 'plughw:CARD=UAC2Gadget,DEV=3')
        for flag, expected in (('-f', 'S16_LE'), ('-c', '2'), ('-r', '48000')):
            self.assertEqual(argv[argv.index(flag) + 1], expected)

    def test_settings_navigation_and_640x480_render(self):
        self.assertIn(self.advanced.ADVANCED_PARAM, self.controller.SETTINGS_PARAMS)
        self.assertEqual(self.controller.SETTINGS_PARAMS[-1], self.usb.PARAM)
        # Native control dispatch reaches appended settings row through DOWN.
        for _ in range(len(self.controller.SETTINGS_PARAMS) - 1):
            self.controller.handle('DOWN')
        self.assertEqual(self.controller.current_param, self.usb.PARAM)
        if os.environ.get('GRAINBERNIK_TEST_OUTPUT'):
            directory = Path(os.environ['GRAINBERNIK_TEST_OUTPUT'])
            directory.mkdir(parents=True, exist_ok=True)
            self.ui.screen.fill(self.ui.BG)
            self.ui.draw(self.controller, self.bus, None, None)
            self.assertEqual(self.controller.current_param, self.usb.PARAM)
            self.pg.display.flip()
            surface = self.pg.transform.smoothscale(self.ui.screen, (640, 480))
            self.pg.image.save(surface, str(directory / 'usb-entry-640.png'))
        self.controller.handle('A')
        self.assertTrue(self.runtime.open)
        self.controller.handle('RIGHT')
        self.assertEqual(self.runtime.settings.data['mode'], 'External USB Audio')
        self.controller.handle('RIGHT')
        self.assertEqual(self.runtime.settings.data['mode'], 'iPhone USB Audio Gadget')
        with patch.object(self.runtime, 'draw', wraps=self.runtime.draw) as render:
            self.ui.draw(self.controller, self.bus, None, None)
            render.assert_called_once_with(self.ui)
        self.pg.display.flip()
        if os.environ.get('GRAINBERNIK_TEST_OUTPUT'):
            directory = Path(os.environ['GRAINBERNIK_TEST_OUTPUT'])
            directory.mkdir(parents=True, exist_ok=True)
            surface = self.pg.transform.smoothscale(self.ui.screen, (640, 480))
            self.pg.image.save(surface, str(directory / 'usb-settings-640.png'))
        self.controller.handle('B')
        self.assertFalse(self.runtime.open)

    def test_start_and_tabs_pass_through_usb_overlay(self):
        self.runtime.open = True
        before = self.bus.get('transport.playing')
        self.controller.handle('START')
        self.assertNotEqual(self.bus.get('transport.playing'), before)
        self.controller.handle('R')
        self.assertFalse(self.runtime.open)
        self.assertNotEqual(self.controller.current_tab, 'SETTINGS')

    def test_physical_a_b_and_dpad_via_native_input(self):
        from engine.input import InputManager

        class Joy:
            def init(self): pass
            def quit(self): pass
            def get_name(self): return 'Integration controller'
            def get_numaxes(self): return 4
            def get_axis(self, index): return 0.0

        with patch.object(self.pg.joystick, 'get_count', return_value=1), \
                patch.object(self.pg.joystick, 'Joystick', return_value=Joy()):
            manager = InputManager()
            self.pg.event.clear()
            for _ in range(len(self.controller.SETTINGS_PARAMS) - 1):
                self.controller.handle('DOWN')
            self.pg.event.post(self.pg.event.Event(self.pg.JOYBUTTONDOWN, button=5, joy=0))
            for action, value in manager.poll(): self.controller.handle(action, value)
            self.assertTrue(self.runtime.open)
            self.pg.event.post(self.pg.event.Event(self.pg.JOYBUTTONUP, button=5, joy=0))
            manager.poll()
            self.pg.event.post(self.pg.event.Event(self.pg.JOYHATMOTION, hat=0, value=(0, -1), joy=0))
            for action, value in manager.poll(): self.controller.handle(action, value)
            self.assertEqual(self.runtime.index, 1)
            self.pg.event.post(self.pg.event.Event(self.pg.JOYBUTTONDOWN, button=4, joy=0))
            for action, value in manager.poll(): self.controller.handle(action, value)
            self.assertFalse(self.runtime.open)
            manager.close()

    def test_advanced_controls_still_reach_real_bus(self):
        runtime = self.advanced._runtime
        runtime.settings.data['l2'].update(enabled=True, effect='Reverse', mode='Hold')
        self.controller.tab_index = self.controller.TABS.index('GRAIN')
        original = self.bus.get('motion.reverse')
        runtime.controls.button('l2', True)
        self.assertEqual(self.bus.get('motion.reverse'), 1.0)
        runtime.controls.button('l2', False)
        self.assertEqual(self.bus.get('motion.reverse'), original)

    def test_bootstrap_does_not_enable_disabled_advanced_adapter(self):
        import types
        from unittest.mock import Mock
        advanced = types.SimpleNamespace(_installed=False, _attach=Mock())
        with patch.object(self.usb, '_installed', False), \
                patch.object(self.usb, '_attach', return_value=True), \
                patch.dict(sys.modules, {'gb_advanced': advanced}), \
                patch.object(self.pg, 'init', return_value='native initialized'):
            self.usb.install()
            self.assertEqual(self.pg.init(), 'native initialized')
            advanced._attach.assert_not_called()


if __name__ == '__main__':
    unittest.main()
