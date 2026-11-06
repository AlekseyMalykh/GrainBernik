"""Hardware-free USB/ALSA safety, routing and lifecycle checks (Python 3.12)."""
import copy
import gzip
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import time
import types
import unittest
from unittest.mock import patch
import wave

APP = Path(__file__).resolve().parents[1] / 'rg40xx-h-patch/grainbrick-beta'
sys.path.insert(0, str(APP))
import gb_usb_gadget as gadget
import gb_usb_audio as audio


class Fixture(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.system = gadget.System(self.root, '4.9.fixture')
        self.cfg = copy.deepcopy(audio.DEFAULT)
        self.cfg['mode'] = audio.MODES[2]
        self.config = self.write('sys/kernel/config/usb_gadget/knulli/configs/c.1/.keep').parent
        self.gadget = self.config.parent.parent
        (self.gadget / 'functions').mkdir()
        (self.gadget / 'UDC').write_text('udc0\n')
        self.write('sys/class/udc/udc0/state', 'configured')
        self.write('sys/class/udc/udc0/function', 'knulli')
        self.settings = audio.Settings(self.root / 'usb.json')
        self.journal = self.root / 'journal.json'
        self.activation = gadget.Activation(self.system, self.journal)

    def tearDown(self):
        self.temp.cleanup()

    def write(self, name, value=''):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(value)
        return path

    def card(self, number=4, card_id='UAC2Gadget', capture=2, playback=3, external=False):
        self.write('proc/asound/card%d/id' % number, card_id)
        self.write('proc/asound/cards', '%d [%s ]: %s - Test\n' % (
            number, card_id, 'USB-Audio' if external else 'UAC2Gadget'))
        if external:
            self.write('proc/asound/card%d/usbid' % number, '1234:5678')
        for dev, direction in ((capture, 'c'), (playback, 'p')):
            if dev is not None:
                self.write('proc/asound/card%d/pcm%d%s/sub0/status' % (number, dev, direction), 'closed')
                self.write('proc/asound/card%d/pcm%d%s/sub0/hw_params' % (number, dev, direction), 'closed')

    def stream(self, direction, pointer, owner=101, state='RUNNING'):
        name = 'pcm2c' if direction == 'capture' else 'pcm3p'
        self.write('proc/asound/card4/%s/sub0/status' % name,
                   'state: %s\nowner_pid: %s\nhw_ptr: %s' % (state, owner, pointer))
        self.write('proc/101/stat', '101 (arecord with spaces) S 100 0 0')
        self.write('proc/102/stat', '102 (aplay) S 100 0 0')


class Discovery(Fixture):
    def test_loaded_module_is_evidence_without_any_ko_file(self):
        self.write('boot/config-4.9.fixture', '# CONFIG_USB_CONFIGFS_F_UAC2 is not set\n')
        self.write('proc/modules', 'usb_f_uac2 1234 0 - Live 0x00\n')
        self.assertEqual(self.system.function_support('uac2')['state'], 'candidate')

    def test_disabled_by_default_and_bad_file_fails_closed(self):
        self.assertEqual(self.settings.data['mode'], 'Disabled')
        self.settings.path.write_text('{broken')
        loaded = audio.Settings(self.settings.path)
        self.assertEqual(loaded.data['mode'], 'Disabled')
        self.assertTrue(loaded.error)

    def test_boolean_and_pcm_validation(self):
        for bad in ({'input': 'yes'}, {'playback_device': -1}, {'mode': 'magic'}, {'channels': 1}):
            self.settings.path.write_text(json.dumps(bad))
            self.assertEqual(audio.Settings(self.settings.path).data, audio.DEFAULT)

    def test_saved_mode_survives_restart(self):
        self.assertTrue(self.settings.save(self.cfg))
        self.assertEqual(audio.Settings(self.settings.path).data, self.cfg)

    def test_failed_save_does_not_change_runtime(self):
        old = copy.deepcopy(self.settings.data)
        with patch.object(audio, 'atomic_json', side_effect=OSError('read-only')):
            self.assertFalse(self.settings.save(self.cfg))
        self.assertEqual(old, self.settings.data)

    def test_missing_kernel_config_is_unknown(self):
        report = self.system.report()
        self.assertIsNone(report['kernel']['source'])
        self.assertEqual(set(report['kernel']['flags'].values()), {'unknown'})

    def test_built_in_is_not_missing_module(self):
        path = self.root / 'proc/config.gz'
        path.parent.mkdir(exist_ok=True)
        path.write_bytes(gzip.compress(b'CONFIG_USB_CONFIGFS_F_UAC2=y\n# CONFIG_SND_ALOOP is not set\n'))
        flags = self.system.kernel()['flags']
        self.assertEqual(flags['USB_CONFIGFS_F_UAC2'], 'y')
        self.assertEqual(flags['SND_ALOOP'], 'n')
        self.assertEqual(flags['USB_F_UAC2'], 'unknown')

    def test_bsp_module_can_exist_despite_disabled_embedded_config(self):
        self.write('boot/config-4.9.fixture', '# CONFIG_USB_CONFIGFS_F_UAC2 is not set\n')
        self.write('lib/modules/4.9.fixture/kernel/drivers/usb/gadget/function/usb_f_uac2.ko', 'fixture')
        support = self.system.function_support('uac2')
        self.assertEqual(support['kernel_flag'], 'n')
        self.assertEqual(support['state'], 'candidate')
        self.assertEqual(self.activation.plan(self.config)['support'], support)
        self.assertIn('conflicts with embedded config', '\n'.join(self.system.report()['notes']))

    def test_stock_uac2_underscore_name_is_detected(self):
        self.card(card_id='UAC2_Gadget')
        self.assertEqual(audio.endpoints(self.system, self.cfg)['card']['id'], 'UAC2_Gadget')

    def test_card_number_and_nonzero_pcms(self):
        self.card(number=9)
        route = audio.endpoints(self.system, self.cfg)
        self.assertEqual(route['capture']['pcm'], 'plughw:CARD=UAC2Gadget,DEV=2')
        self.assertEqual(route['playback']['pcm'], 'plughw:CARD=UAC2Gadget,DEV=3')

    def test_external_usb_is_never_mistaken_for_gadget(self):
        self.card(card_id='Device', external=True)
        with self.assertRaises(audio.AudioError):
            audio.endpoints(self.system, self.cfg)

    def test_half_duplex_is_rejected_when_both_requested(self):
        self.card(capture=None)
        with self.assertRaisesRegex(audio.AudioError, 'capture'):
            audio.endpoints(self.system, self.cfg)
        self.cfg['input'] = False
        self.assertIn('playback', audio.endpoints(self.system, self.cfg))

    def test_multiple_gadgets_require_selection(self):
        self.card(number=4)
        self.card(number=7, card_id='UAC1Gadget')
        with self.assertRaises(audio.AudioError):
            audio.endpoints(self.system, self.cfg)
        self.cfg['card_id'] = 'UAC1Gadget'
        self.assertEqual(audio.endpoints(self.system, self.cfg)['card']['number'], 7)

    def test_multiple_pcm_devices_require_selection(self):
        self.card()
        self.write('proc/asound/card4/pcm5c/sub0/status', 'closed')
        with self.assertRaisesRegex(audio.AudioError, 'ambiguous'):
            audio.endpoints(self.system, self.cfg)
        self.cfg['capture_device'] = 5
        self.assertEqual(audio.endpoints(self.system, self.cfg)['capture']['device'], 5)

    def test_diagnostics_never_opens_pcm_or_changes_files(self):
        self.card()
        before = {str(p): p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        with patch.object(subprocess, 'Popen', side_effect=AssertionError('must not spawn')):
            report = self.system.report()
        self.assertEqual(before, {str(p): p.read_bytes() for p in self.root.rglob('*') if p.is_file()})
        self.assertIn('Current negotiated PCM', '\n'.join(report['notes']))

    def test_commands_have_bounded_timeout_and_report_unavailable(self):
        with patch.object(subprocess, 'run', side_effect=FileNotFoundError('not installed')) as run:
            report = self.system.report(commands=True)
        self.assertEqual(run.call_count, 4)
        self.assertTrue(all(v.get('unavailable') for v in report['commands'].values()))
        self.assertEqual(run.call_args.kwargs['timeout'], 4)


class Status(Fixture):
    def setUp(self):
        super().setUp()
        self.card()
        self.monitor = audio.Monitor(self.system, app_pid=100)

    def test_enumeration_is_not_full_duplex(self):
        self.assertEqual(self.monitor.status(self.cfg), ('USB Connected', 'Audio Device Detected'))

    def test_open_without_progress_is_not_active(self):
        self.stream('capture', 10)
        self.stream('playback', 10, owner=102)
        for _ in range(2):
            self.assertNotEqual(self.monitor.status(self.cfg)[1], 'Full Duplex Active')

    def test_both_owned_pcms_must_progress_simultaneously(self):
        self.stream('capture', 10)
        self.stream('playback', 10, owner=102)
        self.monitor.status(self.cfg)
        self.stream('capture', 20)
        self.stream('playback', 20, owner=102)
        self.assertEqual(self.monitor.status(self.cfg)[1], 'Full Duplex Active')
        self.stream('capture', 20)
        self.stream('playback', 30, owner=102)
        self.assertEqual(self.monitor.status(self.cfg)[1], 'Output Ready')

    def test_foreign_process_is_busy_not_active(self):
        self.stream('capture', 10, owner=999)
        self.assertEqual(self.monitor.status(self.cfg)[1], 'Audio Device Busy')

    def test_unplug_clears_previous_duplex_evidence(self):
        self.stream('capture', 10)
        self.monitor.status(self.cfg)
        self.write('sys/class/udc/udc0/state', 'not attached')
        self.assertEqual(self.monitor.status(self.cfg)[0], 'USB Not Connected')
        self.assertFalse(self.monitor.previous)

    def test_guard_stops_owned_process_on_unplug(self):
        self.settings.save(self.cfg)
        process = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)'])
        try:
            audio.guard(process, 'input', self.settings.path, self.system)
            self.write('sys/class/udc/udc0/state', 'not attached')
            process.wait(timeout=3)
            self.assertIsNotNone(process.returncode)
        finally:
            audio.stop_process(process)

    def test_guard_stops_owned_process_on_mode_disable(self):
        self.settings.save(self.cfg)
        process = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)'])
        try:
            audio.guard(process, 'output', self.settings.path, self.system)
            self.cfg['mode'] = 'Disabled'
            self.settings.save(self.cfg)
            process.wait(timeout=3)
        finally:
            audio.stop_process(process)


class Activation(Fixture):
    def test_known_sunxi_uac2_crash_is_blocked_before_any_write(self):
        from hashlib import sha256

        self.system.release = '4.9.170'
        udc = '5100000.udc-controller'
        self.write('sys/class/udc/' + udc + '/state', 'configured')
        binding = self.gadget / 'UDC'
        binding.write_text(udc + '\n')
        module = self.write('lib/modules/4.9.170/usb_f_uac2.ko', 'module fixture')
        with patch.object(gadget, 'FAULTY_SUNXI_UAC2_SHA256', sha256(module.read_bytes()).hexdigest()):
            self.assertIn('missing USB IN endpoint', self.activation.plan(self.config)['blocked_reason'])
            with self.assertRaisesRegex(gadget.GadgetError, 'missing USB IN endpoint'):
                self.activation.activate(self.config, True)
        self.assertEqual(binding.read_text().strip(), udc)
        self.assertFalse(self.journal.exists())

    def test_unbinding_disconnected_bsp_is_refused(self):
        self.write('sys/class/udc/udc0/state', 'not attached')
        with self.assertRaisesRegex(gadget.GadgetError, 'host must be connected'):
            self.activation.activate(self.config, True)
        self.assertFalse(self.journal.exists())

    def test_dry_plan_is_read_only(self):
        before = sorted(str(p) for p in self.root.rglob('*'))
        plan = self.activation.plan(self.config)
        self.assertEqual(before, sorted(str(p) for p in self.root.rglob('*')))
        self.assertEqual(plan['attributes']['c_chmask'], '3')
        self.assertFalse(self.journal.exists())

    def test_activation_requires_disconnect_acknowledgment(self):
        with self.assertRaises(gadget.GadgetError):
            self.activation.activate(self.config)
        self.assertEqual((self.gadget / 'UDC').read_text(), 'udc0\n')

    def test_known_disabled_uac_is_rejected_before_unbind(self):
        self.write('boot/config-4.9.fixture', '# CONFIG_USB_CONFIGFS_F_UAC2 is not set\n')
        with self.assertRaisesRegex(gadget.GadgetError, 'Driver Not Available'):
            self.activation.activate(self.config, True)
        self.assertFalse(self.journal.exists())

    def test_never_replaces_existing_audio_source(self):
        (self.gadget / 'functions/audio_source.0').mkdir()
        with self.assertRaisesRegex(gadget.GadgetError, 'Existing audio'):
            self.activation.plan(self.config)

    def test_cannot_select_paths_outside_configfs(self):
        with self.assertRaises(gadget.GadgetError):
            self.activation.plan(self.root)

    def test_cannot_take_other_gadgets_udc(self):
        other = self.write('sys/kernel/config/usb_gadget/other/UDC', 'udc0')
        with self.assertRaisesRegex(gadget.GadgetError, 'another gadget'):
            self.activation.plan(self.config)

    def virtual_fs(self, fail_bind=False):
        real_mkdir, real_rmdir, real_write = Path.mkdir, Path.rmdir, Path.write_text
        state = {'failed': False}

        def mkdir(path, *a, **kw):
            result = real_mkdir(path, *a, **kw)
            if path.name in ('uac1.grainbernik', 'uac2.grainbernik'):
                for attr in gadget.ATTRS:
                    (path / attr).write_text('0')
            return result

        def rmdir(path):
            if path.name in ('uac1.grainbernik', 'uac2.grainbernik'):
                for attr in gadget.ATTRS:
                    (path / attr).unlink(missing_ok=True)
            return real_rmdir(path)

        def write(path, data, *a, **kw):
            # Mainline ConfigFS returns ENODEV on an already-unbound UDC.
            if path == self.gadget / 'UDC' and not data.strip() and not gadget.read(path):
                raise OSError(19, 'No such device')
            if fail_bind and path == self.gadget / 'UDC' and data == 'udc0\n' and not state['failed']:
                state['failed'] = True
                raise OSError('bind failed')
            return real_write(path, data, *a, **kw)

        return patch.object(Path, 'mkdir', mkdir), patch.object(Path, 'rmdir', rmdir), patch.object(Path, 'write_text', write)

    def test_initially_unbound_gadget_activates_and_returns_to_unbound(self):
        (self.gadget / 'UDC').write_text('\n')
        self.write('sys/class/udc/udc0/state', 'not attached')
        a, b, c = self.virtual_fs()
        with a, b, c:
            self.activation.activate(self.config, True)
            self.assertEqual(gadget.read(self.gadget / 'UDC'), 'udc0')
            self.activation.restore()
        self.assertEqual(gadget.read(self.gadget / 'UDC'), '')
        self.assertFalse(self.journal.exists())

    def test_failed_bind_of_unbound_gadget_cleans_up_without_unbinding_again(self):
        (self.gadget / 'UDC').write_text('\n')
        a, b, c = self.virtual_fs(fail_bind=True)
        with a, b, c:
            with self.assertRaisesRegex(OSError, 'bind failed'):
                self.activation.activate(self.config, True)
        self.assertEqual(gadget.read(self.gadget / 'UDC'), '')
        self.assertFalse(self.journal.exists())
        self.assertFalse((self.gadget / 'functions/uac2.grainbernik').exists())

    def test_append_preserves_other_functions_and_restores(self):
        foreign = self.gadget / 'functions/ffs.adb'
        foreign.mkdir()
        try:
            (self.config / 'ffs.adb').symlink_to(foreign, target_is_directory=True)
        except OSError:
            self.skipTest('symlink privilege unavailable')
        a, b, c = self.virtual_fs()
        with a, b, c:
            plan = self.activation.activate(self.config, True)
            self.assertTrue((self.config / 'ffs.adb').is_symlink())
            self.assertTrue(Path(plan['link']).is_symlink())
            self.assertEqual((Path(plan['function']) / 'p_srate').read_text().strip(), '48000')
            self.activation.restore()
        self.assertTrue(foreign.exists())
        self.assertFalse(self.journal.exists())
        self.assertEqual((self.gadget / 'UDC').read_text(), 'udc0\n')

    def test_failed_bind_rolls_back(self):
        a, b, c = self.virtual_fs(fail_bind=True)
        with a, b, c:
            with self.assertRaises(OSError):
                self.activation.activate(self.config, True)
        self.assertFalse((self.gadget / 'functions/uac2.grainbernik').exists())
        self.assertFalse(self.journal.exists())
        self.assertEqual((self.gadget / 'UDC').read_text(), 'udc0\n')

    def test_missing_duplex_attributes_rolls_back(self):
        with self.assertRaisesRegex(gadget.GadgetError, 'duplex PCM'):
            self.activation.activate(self.config, True)
        self.assertFalse(self.journal.exists())
        self.assertEqual((self.gadget / 'UDC').read_text(), 'udc0\n')

    def test_restore_rejects_tampered_journal(self):
        plan = self.activation.plan(self.config)
        plan['function'] = str(self.root / 'unrelated')
        gadget.atomic_json(self.journal, plan)
        with self.assertRaisesRegex(gadget.GadgetError, 'Invalid journal'):
            self.activation.restore()
        self.assertTrue(self.journal.exists())


class PCMTests(unittest.TestCase):
    def test_uac_mask_and_format_are_decoded_without_guessing_unknowns(self):
        result = gadget.audio_format({'c_chmask': '3', 'c_ssize': '2', 'c_srate': '48000,44100'}, 'c')
        self.assertEqual(result, {'enabled': True, 'channels': 2,
                                  'advertised_rates': [48000, 44100], 'sample_bits': 16})
        unknown = gadget.audio_format(dict.fromkeys(('p_chmask', 'p_ssize', 'p_srate')), 'p')
        self.assertIsNone(unknown['enabled'])
        self.assertIsNone(unknown['channels'])

    def test_wav_metrics_distinguishes_signal_from_silence(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / 'capture.wav'
            for sample, expected in ((0, False), (1000, True)):
                with wave.open(str(path), 'wb') as wav:
                    wav.setparams((2, 2, 48000, 0, 'NONE', ''))
                    wav.writeframes(struct.pack('<hh', sample, sample) * 512)
                self.assertEqual(audio.wav_metrics(path)['non_silent'], expected)



class EngineHooks(Fixture):
    def test_native_enumeration_and_only_owned_pcm_processes_are_guarded(self):
        self.card()
        self.settings.save(self.cfg)
        inputs, outputs = types.ModuleType('engine.audio_inputs'), types.ModuleType('engine.audio_devices')
        inputs.available_usb_captures = lambda: [{'pcm': 'external'}]
        outputs.available_outputs = lambda: [('internal', 'INTERNAL', 'default')]

        class Process:
            def __init__(self, args, *a, **kw):
                self.args = args

        with patch.dict(sys.modules, {'engine.audio_inputs': inputs, 'engine.audio_devices': outputs}), \
                patch.object(subprocess, 'Popen', Process), patch.object(audio, 'guard') as guard:
            self.assertTrue(audio.install_engine_hooks(self.settings.path, self.system))
            self.assertEqual(inputs.available_usb_captures()[0]['pcm'], 'plughw:CARD=UAC2Gadget,DEV=2')
            self.assertEqual(outputs.available_outputs()[-1][2], 'plughw:CARD=UAC2Gadget,DEV=3')
            subprocess.Popen(['aplay', '-D', 'default'])
            guard.assert_not_called()


            subprocess.Popen(['arecord', '-D', 'plughw:CARD=UAC2Gadget,DEV=2'])
            self.assertEqual(guard.call_args.args[1], 'input')
            subprocess.Popen(['aplay', '-D', 'plughw:CARD=UAC2Gadget,DEV=3'])
            self.assertEqual(guard.call_args.args[1], 'output')
            self.cfg['mode'] = 'Disabled'
            self.settings.save(self.cfg)
            self.assertEqual(inputs.available_usb_captures(), [{'pcm': 'external'}])
            self.assertEqual(outputs.available_outputs(), [('internal', 'INTERNAL', 'default')])

    def test_unavailable_gadget_does_not_prevent_internal_output(self):
        self.settings.save(self.cfg)
        inputs, outputs = types.ModuleType('engine.audio_inputs'), types.ModuleType('engine.audio_devices')
        inputs.available_usb_captures = lambda: []
        outputs.available_outputs = lambda: [('internal', 'INTERNAL', 'default')]

        class Process:
            def __init__(self, args, *a, **kw): self.args = args

        with patch.dict(sys.modules, {'engine.audio_inputs': inputs, 'engine.audio_devices': outputs}), \
                patch.object(subprocess, 'Popen', Process), patch.object(audio, 'guard') as guard:
            audio.install_engine_hooks(self.settings.path, self.system)
            self.assertEqual(subprocess.Popen(['aplay', '-D', 'default']).args[-1], 'default')
            guard.assert_not_called()


class DiagnosticPCM(Fixture):
    def test_duplex_test_uses_both_pcms_and_reports_non_silent_wav(self):
        self.card()
        opened = []

        class Process:
            def __init__(self, argv, **kwargs):
                self.returncode = 0
                opened.append(argv)
                if argv[0] == 'arecord':
                    with wave.open(argv[-1], 'wb') as wav:
                        wav.setparams((2, 2, 48000, 0, 'NONE', ''))
                        wav.writeframes(struct.pack('<hh', 1000, -1000) * 512)

            def poll(self): return self.returncode

        with patch.object(subprocess, 'Popen', Process):
            result = audio.pcm_test(self.root / 'test', 1, system=self.system, settings_path=self.settings.path)
        self.assertEqual(opened[0][opened[0].index('-D') + 1], 'plughw:CARD=UAC2Gadget,DEV=2')
        self.assertEqual(opened[1][opened[1].index('-D') + 1], 'plughw:CARD=UAC2Gadget,DEV=3')
        self.assertTrue(result['capture']['non_silent'])
        self.assertFalse(result['iphone_recording_verified'])

    def test_failed_pcm_test_retains_report_and_logs(self):
        self.card()

        class Process:
            def __init__(self, argv, **kwargs):
                self.returncode = 1
                kwargs['stderr'].write('Device or resource busy\n')

            def poll(self): return self.returncode

        with patch.object(subprocess, 'Popen', Process), self.assertRaises(audio.AudioError):
            audio.pcm_test(self.root / 'test', 1, capture=True, playback=False,
                           system=self.system, settings_path=self.settings.path)
        report = json.loads((self.root / 'test/results.json').read_text())
        self.assertTrue(report['capture']['xrun_or_error'])
        self.assertIn('aborted', report)

    def test_existing_wav_is_never_overwritten(self):
        self.card()
        path = self.write('test/capture.wav', 'precious existing audio')
        with self.assertRaisesRegex(audio.AudioError, 'already exist'):
            audio.pcm_test(path.parent, 1, system=self.system, settings_path=self.settings.path)
        self.assertEqual(path.read_text(), 'precious existing audio')


if __name__ == '__main__':
    unittest.main()
