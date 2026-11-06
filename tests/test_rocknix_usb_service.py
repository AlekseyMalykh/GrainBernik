"""Mode changes must bind once, restore when disabled, and respect USB owners."""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / 'rg40xx-h-patch/grainbrick-beta'))
spec = importlib.util.spec_from_file_location('gb_usb_service', REPO / 'tools/legacy-rocknix-test-image/rocknix/gb_usb_service.py')
service = importlib.util.module_from_spec(spec)
spec.loader.exec_module(service)


class USBService(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.system = service.System(self.root, '7.1.2-gb-uac2')
        self.base = self.root / 'sys/kernel/config/usb_gadget'
        self.base.mkdir(parents=True)
        self.settings = service.Settings(self.root / 'settings.json')
        self.activation = Mock()
        self.activation.journal = self.root / 'journal.json'
        self.worker = service.Service(self.system, self.settings, self.activation)

    def mode(self, mode):
        data = self.settings.load()
        data['mode'] = mode
        self.settings.save(data)

    def active(self):
        gadget = self.base / 'grainbernik'
        gadget.mkdir()
        (gadget / 'UDC').write_text('udc0\n')
        self.activation.journal.write_text(json.dumps({'gadget': str(gadget), 'udc': 'udc0'}))
        return gadget

    def test_disabled_never_creates_or_binds_gadget(self):
        self.worker.tick()
        self.assertEqual(list(self.base.iterdir()), [])
        self.activation.activate.assert_not_called()
        self.activation.restore.assert_not_called()

    def test_phone_mode_activates_both_directions_at_48k(self):
        self.mode(service.MODES[2])
        with patch.object(service, 'scaffold', return_value=self.root / 'config'):
            self.worker.tick()
        self.activation.activate.assert_called_once_with(self.root / 'config', allow_disconnect=True, rate=48000)

    def test_active_mode_does_not_rebind_on_each_poll(self):
        self.mode(service.MODES[2])
        self.active()
        self.worker.tick()
        self.activation.activate.assert_not_called()
        self.activation.restore.assert_not_called()

    def test_disabled_or_external_mode_restores_owned_gadget(self):
        self.active()
        for mode in service.MODES[:2]:
            self.mode(mode)
            self.worker.tick()
        self.assertEqual(self.activation.restore.call_count, 2)
        self.activation.activate.assert_not_called()

    def test_invalid_settings_restore_instead_of_enabling(self):
        self.active()
        self.settings.path.write_text('{broken')
        self.worker.tick()
        self.activation.restore.assert_called_once()

    def test_changed_usb_owner_is_reported_without_rebinding(self):
        self.mode(service.MODES[2])
        gadget = self.active()
        (gadget / 'UDC').write_text('different-udc\n')
        with self.assertRaisesRegex(service.GadgetError, 'changed outside'):
            self.worker.tick()
        self.activation.activate.assert_not_called()

    def test_stock_kernel_rejected_before_configfs_writes(self):
        self.system.release = '4.9.170'
        with self.assertRaisesRegex(service.GadgetError, 'dedicated'):
            service.scaffold(self.system)
        self.assertEqual(list(self.base.iterdir()), [])

    def test_foreign_bound_gadget_is_preserved(self):
        other = self.base / 'cdc'
        other.mkdir()
        (other / 'UDC').write_text('udc0')
        with self.assertRaisesRegex(service.GadgetError, 'belongs to cdc'):
            service.scaffold(self.system)
        self.assertEqual((other / 'UDC').read_text(), 'udc0')
        self.assertFalse((self.base / 'grainbernik').exists())

    def test_same_name_with_another_owner_is_rejected(self):
        (self.base / 'grainbernik').mkdir()
        with self.assertRaisesRegex(service.GadgetError, 'another owner'):
            service.scaffold(self.system)

    def test_scaffold_is_unbound_and_has_explicit_device_identity(self):
        real_mkdir = Path.mkdir

        def configfs_mkdir(path, *args, **kwargs):
            result = real_mkdir(path, *args, **kwargs)
            if path == self.base / 'grainbernik':
                (path / 'strings').mkdir()
                (path / 'configs').mkdir()
                (path / 'UDC').write_text('')
            elif path == self.base / 'grainbernik/configs/c.1':
                (path / 'strings').mkdir()
            return result

        with patch.object(Path, 'mkdir', configfs_mkdir):
            config = service.scaffold(self.system)
        gadget = config.parent.parent
        self.assertEqual((gadget / 'UDC').read_text(), '')
        self.assertEqual((gadget / 'strings/0x409/product').read_text().strip(), 'GrainBernik USB Audio')
        self.assertEqual((config / 'bmAttributes').read_text().strip(), '0xc0')
        self.assertEqual(service.scaffold(self.system), config)


if __name__ == '__main__':
    unittest.main()
