"""Optional real 1.0.1 menu/navigation/hotplug integration; isolated app data."""
import importlib
import os
from pathlib import Path
import platform
import sys
import tempfile
import unittest
from unittest.mock import patch

OFFICIAL = os.environ.get('GRAINBRICK_OFFICIAL_DIR')
SUPPORTED = bool(OFFICIAL and platform.machine().lower() in ('aarch64', 'arm64')
                 and sys.version_info[:2] == (3, 12))


@unittest.skipUnless(SUPPORTED, 'requires official ARM64 1.0.1 and Python 3.12')
class QuickSettingsIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='gb-quick-native-')
        cls.root = Path(cls.temp.name)
        official = Path(OFFICIAL)
        for p in official.iterdir():
            if p.suffix == '.so' or p.name in ('resources', 'libSoundTouch.so.1'):
                (cls.root / p.name).symlink_to(p)
        os.environ['GRAINBRICK_ROOT'] = str(cls.root)
        sys.path[:0] = [str(Path(__file__).resolve().parents[1] / 'rg40xx-h-patch/grainbrick-beta'),
                       str(official), str(official / '_vendor')]
        import pygame
        import gb_usb_audio as audio
        audio.CONFIG = cls.root / 'gb_usb_audio.json'
        import gb_advanced, gb_usb_settings, gb_quick_settings
        cls.pg, cls.quick, cls.advanced, cls.usb = pygame, gb_quick_settings, gb_advanced, gb_usb_settings
        cls.gadget_patch = patch.object(gb_usb_settings.gadget, 'active', return_value=False)
        cls.gadget_patch.start()
        cls.start_patch = patch.object(gb_usb_settings.gadget, 'start')
        cls.start_patch.start()

        class Stop(Exception): pass

        def stop():
            raise Stop()

        original = pygame.init
        pygame.init = stop
        for module in (gb_advanced, gb_usb_settings, gb_quick_settings):
            module.install()
        try:
            importlib.import_module('main')
        except Stop:
            pass
        finally:
            pygame.init = original
        from engine.control import ControlManager
        from engine.parameters import create_default_parameters
        from ui.renderer import UIEngine
        cls.C, cls.U, cls.bus = ControlManager, UIEngine, staticmethod(create_default_parameters)
        UIEngine.SETTINGS_PATH = str(cls.root / 'settings.json')
        cls.input_module, cls.output_module = sys.modules['engine.audio_inputs'], sys.modules['engine.audio_devices']
        pygame.init()

    @classmethod
    def tearDownClass(cls):
        cls.start_patch.stop()
        cls.gadget_patch.stop()
        cls.pg.quit()
        cls.temp.cleanup()

    def setUp(self):
        self.captures, self.outputs = [], [('internal', 'INTERNAL', 'default')]
        self.input_module._grainbernik_native_captures = lambda: list(self.captures)
        self.output_module._grainbernik_native_outputs = lambda: list(self.outputs)
        self.controller = self.C(self.bus())
        self.ui = self.U()
        self.runtime = self.quick._runtime
        self.controller.tab_index = self.controller.TABS.index('SETTINGS')

    def choose(self, index):
        self.controller.settings_param_index = index
        self.controller.handle('A')

    def test_quick_and_detailed_sections_are_adjacent_and_reachable(self):
        self.assertEqual(self.controller.SETTINGS_PARAMS, self.quick.ROOT)
        self.choose(0)
        self.assertTrue(self.runtime.audio)
        self.controller.handle('B')
        self.assertFalse(self.runtime.audio)
        self.choose(1)
        self.assertTrue(self.usb._runtime.open)
        self.assertIn('native_output', [r[0] for r in self.usb._runtime.rows()])
        self.controller.handle('B')
        self.choose(2)
        self.assertEqual(self.advanced._runtime.menu.page, 'presets')
        self.controller.handle('B')
        self.assertIsNone(self.advanced._runtime.menu.page)
        self.choose(3)
        self.assertEqual(self.advanced._runtime.menu.page, 'root')
        self.controller.handle('B')
        self.choose(4)
        self.assertTrue(self.runtime.more)
        self.assertNotIn('settings.audio_output', self.controller.SETTINGS_PARAMS)
        self.controller.handle('B')
        self.assertEqual(self.controller.SETTINGS_PARAMS, self.quick.ROOT)

    def test_usb_connect_selects_input_and_output_then_unplug_restores_internal(self):
        self.captures.append({'card_id': 'FM1', 'label': 'ChoralRoot FM-1'})
        self.outputs.append(('FM1', 'FM1', 'plughw:CARD=FM1,DEV=0'))
        with patch.object(self.ui, 'refresh_audio_outputs'):
            self.runtime.last_scan = 0
            self.runtime.tick()
            self.assertEqual(self.runtime.capture_id, 'FM1')
            self.assertEqual(self.ui.audio_output_id, 'FM1')
            self.captures.clear()
            self.outputs.pop()
            self.runtime.last_scan = 0
            self.runtime.tick()
            self.assertIsNone(self.runtime.capture_id)
            self.assertEqual(self.ui.audio_output_id, 'internal')

    def test_capture_only_device_keeps_builtin_playback(self):
        self.captures.append({'card_id': 'FM1', 'label': 'ChoralRoot FM-1'})
        self.runtime.last_scan = 0
        self.runtime.tick()
        self.assertEqual(self.runtime.capture_id, 'FM1')
        self.assertEqual(self.ui.audio_output_id, 'internal')

    def test_settings_pages_render_at_640x480(self):
        out = os.environ.get('GRAINBERNIK_TEST_OUTPUT')
        if not out:
            self.skipTest('set GRAINBERNIK_TEST_OUTPUT for visual QA')
        Path(out).mkdir(parents=True, exist_ok=True)
        for name, index in [('settings', None), ('audio', 0), ('audio-advanced', 1),
                            ('controls', 2), ('controls-advanced', 3), ('other', 4)]:
            if index is not None:
                self.choose(index)
            self.ui.screen.fill(self.ui.BG)
            self.ui.draw_settings_page(self.controller)
            surface = self.pg.transform.smoothscale(self.ui.screen, (640, 480))
            self.pg.image.save(surface, str(Path(out) / (name + '.png')))
            if index is not None:
                self.controller.handle('B')


if __name__ == '__main__':
    unittest.main()
