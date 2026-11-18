"""Beta 2.0 port, step 1: bootstrap, launcher and packager.

Always-on tests need no official files. Tests that use the official BETA 2.0
package are skipped unless these are set (never redistributed here):

    GRAINBRICK_BETA2_ZIP=/path/to/GrainBrick_BETA_2_0.zip
"""
import ast
import os
from pathlib import Path
import py_compile
import subprocess
import tempfile
import unittest
import zipfile

REPO = Path(__file__).resolve().parents[1]
BETA2 = REPO / 'rg40xx-h-patch' / 'grainbrick-beta2'
LAUNCH = BETA2 / 'gb_launch.py'
SCRIPT = REPO / 'rocknix' / 'GrainBrick BETA 2.0.sh'
ZIP = os.environ.get('GRAINBRICK_BETA2_ZIP')


class StaticTests(unittest.TestCase):
    def test_bootstrap_compiles(self):
        with tempfile.TemporaryDirectory() as tmp:
            py_compile.compile(str(LAUNCH), cfile=str(Path(tmp) / 'x.pyc'), doraise=True)

    def test_shell_scripts_parse(self):
        for script in (SCRIPT, REPO / 'rocknix' / 'install.sh', REPO / 'rocknix' / 'make_package.sh'):
            subprocess.run(['sh', '-n', str(script)], check=True)

    def test_bootstrap_loads_only_verified_adapters(self):
        tree = ast.parse(LAUNCH.read_text())
        loaded = [n.value.args[0].value for n in ast.walk(tree)
                  if isinstance(n, ast.Expr) and isinstance(n.value, ast.Call)
                  and getattr(n.value.func, 'id', '') == '_load_adapter']
        self.assertEqual(loaded, ['gb_shutdown', 'gb_usb_settings', 'gb_advanced2'])

    def test_launcher_paths(self):
        text = SCRIPT.read_text()
        self.assertIn("APP='/storage/roms/ports/grainbrick-beta2'", text)
        self.assertIn('SDL_AUDIODRIVER=dummy', text)
        self.assertNotIn('GRAINBRICK_BUTTONS', text)  # BETA 2.0 has no gb_buttons layer


@unittest.skipUnless(ZIP and Path(ZIP).is_file(), 'GRAINBRICK_BETA2_ZIP not set')
class OfficialPackageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.src = Path(cls.tmp.name) / 'official'
        with zipfile.ZipFile(ZIP) as archive:
            archive.extractall(cls.src)
        cls.app = cls.src / 'grainbrick-beta2'

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def source(self, rel):
        return ast.parse((self.app / rel).read_text())

    def test_hook_points_exist(self):
        """Names the adapters rely on are still defined in BETA 2.0."""
        def methods(rel, cls):
            for node in self.source(rel).body:
                if isinstance(node, ast.ClassDef) and node.name == cls:
                    return {n.name for n in node.body if isinstance(n, ast.FunctionDef)}
            self.fail('%s missing in %s' % (cls, rel))
        self.assertIn('stop', methods('engine/audio_worker.py', 'AudioWorker'))
        self.assertTrue({'poll', 'close'} <= methods('engine/input.py', 'InputManager'))
        self.assertTrue({'handle'} <= methods('engine/control.py', 'ControlManager'))
        self.assertTrue({'draw_settings_page', '_save_settings', 'footer_hint',
                         'refresh_audio_outputs'} <= methods('ui/renderer.py', 'UIEngine'))

    def test_worker_keeps_process_attribute(self):
        text = (self.app / 'engine' / 'audio_worker.py').read_text()
        self.assertIn('self.process', text)

    def test_main_is_a_script_importable_by_name(self):
        text = (self.app / 'main.py').read_text()
        self.assertNotIn("if __name__", text)  # runs on import, as gb_launch expects

    def test_package_builder(self):
        out = Path(self.tmp.name) / 'package'
        subprocess.run(['sh', str(REPO / 'rocknix' / 'make_package.sh'), ZIP, str(out)],
                       check=True, capture_output=True)
        app = out / 'grainbrick-beta2'
        self.assertTrue((app / 'main.py').is_file())
        self.assertEqual((app / 'gb_launch.py').read_bytes(), LAUNCH.read_bytes())
        for name in ('gb_shutdown', 'gb_usb_settings', 'gb_usb_audio', 'gb_usb_gadget', 'gb_pipewire',
                     'gb_settings_rows', 'gb_advanced2', 'gb_advanced2_controls'):
            self.assertTrue((app / (name + '.py')).is_file(), name)
        # BETA 2.0 has its own page; the 1.0.1 page (fixed 1.0.1 layout) must not ship.
        self.assertEqual((app / 'gb_usb_settings.py').read_bytes(), (BETA2 / 'gb_usb_settings.py').read_bytes())
        self.assertFalse((app / 'gb_advanced.py').exists())
        self.assertTrue((out / 'GrainBrick BETA 2.0.sh').is_file())
        self.assertFalse((out / 'GrainBrick beta 1.0.1.sh').exists())
        self.assertTrue((out / 'install.sh').is_file() and (out / 'uac2').is_dir())

    def test_builder_rejects_unrelated_zip(self):
        bad = Path(self.tmp.name) / 'bad.zip'
        with zipfile.ZipFile(bad, 'w') as archive:
            archive.writestr('readme.txt', 'x')
        result = subprocess.run(['sh', str(REPO / 'rocknix' / 'make_package.sh'), str(bad),
                                 str(Path(self.tmp.name) / 'o2')], capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)


if __name__ == '__main__':
    unittest.main()
