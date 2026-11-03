import copy
import importlib.util
import json
import math
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('advanced_core', ROOT / 'rg40xx-h-patch/grainbrick-beta/gb_advanced_controls.py')
core = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(core)


class Param:
    def __init__(self, value=.5, minimum=0, maximum=1):
        self.value, self.minimum, self.maximum = value, minimum, maximum


class Bus:
    """Same API as the official ParameterBus; real-module tests are separate."""
    def __init__(self):
        keys = set(k for macro in core.BUTTON_EFFECTS.values() for k in macro)
        keys.update(k for k, label in core.AXIS_PARAMETERS)
        keys.difference_update(('filter.cutoff', 'filter.resonance', 'tape.speed', 'pan'))
        self.params = {k: Param() for k in keys}
        self.params['grain.pitch'] = Param(0, -24, 24)
        self.params['reverb.decay'] = Param(6, .3, 20)
        self.params.update({key: Param(value, low, high) for key, (value, low, high) in {
            'orbix.balls': (6, 1, 12), 'orbix.root': (2, 0, 11), 'orbix.scale': (0, 0, 4),
            'orbix.instrument': (0, 0, 2), 'orbix.octave': (0, -2, 2), 'orbix.shape': (3, 0, 5),
            'orbix.enabled': (0, 0, 1), 'orbix.rotation': (18, -55, 55),
            'orbix.gravity': (180, 0, 420), 'orbix.volume': (65, 0, 100),
        }.items()})
        self.writes = []

    def get(self, key):
        return self.params[key].value

    def set(self, key, value):
        param = self.params[key]
        param.value = max(param.minimum, min(param.maximum, value))
        self.writes.append((key, param.value))


class AdvancedTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'settings.json'
        self.store = core.Settings(self.path)
        self.bus = Bus()
        self.controls = core.Controls(self.bus, self.store)
        self.menu = core.Menu(self.store, self.controls)

    def stick(self, name='left_stick', **changes):
        self.store.data[name].update(enabled=True, x='grain.position', smoothing=0, **changes)

    def button(self, name='l2', **changes):
        cfg = dict(enabled=True, effect='Delay Throw', mode='Hold')
        cfg.update(changes)
        self.store.data[name].update(cfg)

    def test_disabled_default_never_writes(self):
        for name in core.CONTROLS:
            self.assertFalse(self.store.data[name]['enabled'])
        self.controls.button('l2', True)
        self.controls.button('r2', True)
        self.controls.tick(dict(enumerate((1, -1, 1, -1))), 0)
        self.assertEqual(self.bus.writes, [])

    def test_all_four_independent_and_reenable_keeps_assignments(self):
        self.stick()
        self.stick('right_stick')
        self.button()
        self.button('r2', effect='Reverb Wash')
        original = copy.deepcopy(self.store.data)
        for name in core.CONTROLS:
            with self.subTest(name=name):
                self.store.data = copy.deepcopy(original)
                self.menu.page = name
                self.menu.index = 0
                self.menu.handle('A')
                self.assertFalse(self.store.data[name]['enabled'])
                for other in core.CONTROLS:
                    if other != name:
                        self.assertEqual(self.store.data[other], original[other])
                self.menu.handle('A')
                self.assertEqual(self.store.data[name], original[name])

    def test_round_trip_preserves_original_and_future_app_keys(self):
        self.path.write_text(json.dumps({'info_language': 'DE', 'future': {'a': 1}}))
        self.stick(mode='Latch', deadzone=23, invert_y=True)
        self.button('r2', mode='Toggle')
        self.assertTrue(self.store.save())
        self.assertEqual(core.Settings(self.path).data, self.store.data)
        saved = json.loads(self.path.read_text())
        self.assertEqual(saved['info_language'], 'DE')
        self.assertEqual(saved['future'], {'a': 1})
        self.assertFalse(self.path.with_name('settings.json.advanced.tmp').exists())

    def test_corrupt_file_is_reported_and_not_overwritten(self):
        self.path.write_text('{broken')
        store = core.Settings(self.path)
        self.assertTrue(store.error)
        self.assertFalse(store.save())
        self.assertEqual(self.path.read_text(), '{broken')

    def test_validate_untrusted_config(self):
        self.assertEqual(core.validate([]), core.defaults())
        self.assertEqual(core.validate({'version': 99}), core.defaults())
        raw = {'left_stick': dict(enabled='yes', deadzone=float('nan'), sensitivity=1e6,
                                  smoothing=-99, mode='invalid', x=[], y='not.real')}
        data = core.validate(raw)['left_stick']
        self.assertFalse(data['enabled'])
        self.assertEqual((data['deadzone'], data['sensitivity'], data['smoothing']), (12, 200, 0))
        self.assertIsNone(data['x'])
        self.assertEqual(data['mode'], 'Spring')

    def test_unsupported_parameters_and_macros_not_offered(self):
        keys = dict(self.controls.axis_choices())
        self.assertNotIn('pan', keys)
        self.assertNotIn('filter.cutoff', keys)
        del self.bus.params['motion.hold']
        self.assertNotIn('Freeze', self.controls.effect_choices())
        self.assertNotIn('Tape Stop', self.controls.effect_choices())

    def test_spring_deadzone_invert_sensitivity_and_bounds(self):
        self.stick(sensitivity=200, invert_x=True)
        self.controls.tick({0: .1, 1: 0}, 0)
        self.assertEqual(self.bus.writes, [])
        self.controls.tick({0: 1, 1: 0}, .1)
        self.assertEqual(self.bus.get('grain.position'), 0)
        self.controls.tick({0: 0, 1: 0}, .2)
        self.assertEqual(self.bus.get('grain.position'), .5)

    def test_smoothing_is_time_based_and_converges(self):
        self.stick()
        self.store.data['left_stick']['smoothing'] = 100
        self.controls.tick({0: 1, 1: 0}, 0)
        self.assertGreater(self.bus.get('grain.position'), .5)
        self.assertLess(self.bus.get('grain.position'), 1)
        for i in range(1, 150):
            self.controls.tick({0: 1, 1: 0}, i / 60)
        self.assertEqual(self.bus.get('grain.position'), 1)
        for i in range(150, 300):
            self.controls.tick({0: 0, 1: 0}, i / 60)
        self.assertEqual(self.bus.get('grain.position'), .5)
        self.assertEqual(self.controls.sources, {})

    def test_latch_keeps_last_value_at_center(self):
        self.stick(mode='Latch')
        self.controls.tick({0: .6, 1: 0}, 0)
        last = self.bus.get('grain.position')
        self.controls.tick({0: 0, 1: 0}, .1)
        self.assertEqual(self.bus.get('grain.position'), last)

    def test_none_axis_and_excluded_trigger_axes_do_not_write(self):
        self.stick()
        self.store.data['left_stick']['x'] = None
        self.controls.tick({0: 1, 1: 1}, 0)
        self.assertEqual(self.bus.writes, [])
        self.store.data['left_stick']['x'] = 'grain.position'
        self.controls.tick({0: 1, 1: 1}, .1, excluded_axes=(0,))
        self.assertEqual(self.bus.writes, [])

    def test_unavailable_unassigned_y_does_not_disable_x(self):
        self.stick()
        self.controls.tick({0: 1}, 0, excluded_axes=(1,))
        self.assertEqual(self.bus.get('grain.position'), 1)

    def test_orbix_axes_persist_without_changing_existing_assignments(self):
        self.store.data['left_stick'].update(enabled=True, x='orbix.rotation', y='orbix.gravity')
        self.store.data['right_stick'].update(enabled=True, x='delay.mix', y='grain.pitch')
        self.button('r2', effect='ORBIX', mode='Toggle')
        self.assertTrue(self.store.save())
        self.assertEqual(core.Settings(self.path).data, self.store.data)
        self.assertIn('orbix.gravity', dict(self.controls.axis_choices()))
        del self.bus.params['orbix.gravity']
        self.assertNotIn('orbix.gravity', dict(self.controls.axis_choices()))
        del self.bus.params['orbix.enabled']
        self.assertNotIn('ORBIX', self.controls.effect_choices())

    def test_orbix_discrete_axes_publish_integer_changes_and_restore(self):
        self.stick()
        for key in core.DISCRETE_PARAMETERS:
            with self.subTest(key=key):
                self.store.data['left_stick']['x'] = key
                initial = self.bus.get(key)
                self.bus.writes.clear()
                self.controls.tick({0: .61, 1: 0}, 0)
                self.assertEqual(self.bus.get(key), round(self.bus.get(key)))
                count = len(self.bus.writes)
                self.controls.tick({0: .61, 1: 0}, .1)
                self.assertEqual(len(self.bus.writes), count)
                self.controls.tick({0: 0, 1: 0}, .2)
                self.assertEqual(self.bus.get(key), initial)
                self.assertTrue(all(v == round(v) for k, v in self.bus.writes if k == key))

    def test_orbix_enable_hold_toggle_and_cancel_restore_prior_state(self):
        for initial in (0, 1):
            for mode in ('Hold', 'Toggle'):
                with self.subTest(initial=initial, mode=mode):
                    self.bus.set('orbix.enabled', initial)
                    self.button('l2', effect='ORBIX', mode=mode)
                    self.controls.button('l2', True)
                    self.assertEqual(self.bus.get('orbix.enabled'), 1)
                    self.controls.button('l2', False)
                    if mode == 'Toggle':
                        self.assertEqual(self.bus.get('orbix.enabled'), 1)
                        self.controls.button('l2', True)
                        self.controls.button('l2', False)
                    self.assertEqual(self.bus.get('orbix.enabled'), initial)
        self.bus.set('orbix.enabled', 0)
        self.controls.button('l2', True)
        self.controls.cancel()
        self.assertEqual(self.bus.get('orbix.enabled'), 0)

    def test_all_four_sources_act_simultaneously(self):
        self.stick()
        self.stick('right_stick')
        self.store.data['right_stick']['x'] = 'grain.spray'
        self.button('l2')
        self.button('r2', effect='Reverb Wash')
        self.controls.button('l2', True)
        self.controls.button('r2', True)
        self.controls.tick({0: 1, 1: 0, 2: -1, 3: 0}, 0)
        self.assertEqual(self.bus.get('grain.position'), 1)
        self.assertEqual(self.bus.get('grain.spray'), 0)
        self.assertEqual(self.bus.get('delay.mix'), .65)
        self.assertEqual(self.bus.get('reverb.mix'), .85)
        self.store.data['left_stick']['enabled'] = False
        self.controls.tick({0: 1, 1: 0, 2: -1, 3: 0}, .1)
        self.assertEqual(self.bus.get('grain.position'), .5)
        self.assertEqual(self.bus.get('grain.spray'), 0)
        self.assertEqual(self.bus.get('delay.mix'), .65)
        self.assertEqual(self.bus.get('reverb.mix'), .85)

    def test_hold_releases_and_native_edit_is_preserved(self):
        self.button()
        initial = self.bus.get('delay.mix')
        self.controls.button('l2', True)
        self.assertEqual(self.bus.get('delay.mix'), .65)
        self.bus.set('delay.mix', .2)
        self.controls.button('l2', False)
        self.assertEqual(self.bus.get('delay.mix'), .2)
        self.assertNotEqual(initial, .2)

    def test_toggle_edges_not_repeated_button_down(self):
        self.button(mode='Toggle')
        self.controls.button('l2', True)
        self.controls.button('l2', True)
        self.controls.button('l2', False)
        self.assertEqual(self.bus.get('delay.mix'), .65)
        self.controls.button('l2', True)
        self.assertEqual(self.bus.get('delay.mix'), .5)

    def test_overlapping_effects_release_in_both_orders(self):
        for first in ('l2', 'r2'):
            with self.subTest(first=first):
                self.button('l2')
                self.button('r2')
                self.controls.button('l2', True)
                self.controls.button('r2', True)
                self.controls.button(first, False)
                self.assertEqual(self.bus.get('delay.mix'), .65)
                self.controls.button('r2' if first == 'l2' else 'l2', False)
                self.assertEqual(self.bus.get('delay.mix'), .5)

    def test_disabling_one_active_control_keeps_other(self):
        self.button('l2')
        self.button('r2', effect='Reverb Wash')
        self.controls.button('l2', True)
        self.controls.button('r2', True)
        self.menu.page = 'l2'
        self.menu.handle('A')
        self.assertEqual(self.bus.get('delay.mix'), .5)
        self.assertEqual(self.bus.get('reverb.mix'), .85)

    def test_menu_exit_clears_hold_toggle_latch_and_requires_new_gesture(self):
        self.button(mode='Toggle')
        self.stick(mode='Latch')
        self.controls.button('l2', True)
        self.controls.tick({0: 1, 1: 0}, 0)
        self.controls.tick({}, .1, performance=False)
        self.assertEqual(self.bus.get('delay.mix'), .5)
        self.assertEqual(self.bus.get('grain.position'), .5)
        self.controls.tick({0: 1, 1: 0}, .2)
        self.controls.button('l2', True)
        self.assertEqual(self.bus.get('grain.position'), .5)
        self.assertEqual(self.bus.get('delay.mix'), .5)
        self.controls.tick({0: 0, 1: 0}, .3)
        self.controls.tick({0: 1, 1: 0}, .4)
        self.assertEqual(self.bus.get('grain.position'), 1)

    def test_reset_confirmation_and_options_scroll_navigation(self):
        self.stick()
        self.menu.open()
        self.menu.handle('A')
        for _ in range(3): self.menu.handle('DOWN')
        self.menu.handle('A')
        self.assertEqual(self.menu.page, 'left_stick.options')
        for _ in range(8): self.menu.handle('DOWN')
        self.assertEqual(self.menu.rows()[self.menu.index][0], 'back')
        self.menu.handle('B')
        self.menu.handle('B')
        for _ in range(5): self.menu.handle('DOWN')
        self.menu.handle('A')
        self.assertTrue(self.menu.confirm)
        self.menu.handle('B')
        self.assertTrue(self.store.data['left_stick']['enabled'])
        self.menu.handle('A')
        self.menu.handle('DOWN')
        self.menu.handle('A')
        self.assertEqual(self.store.data, core.defaults())
        self.menu.handle('B')
        self.assertIsNone(self.menu.page)

    def preset_action(self, key, confirm=True):
        self.menu.page = 'presets'
        self.menu.index = [row[0] for row in self.menu.rows()].index(key)
        self.menu.handle('A')
        if confirm and self.menu.confirm:
            self.menu.handle('DOWN')
            self.menu.handle('A')

    def test_factory_layouts_are_supported_and_keep_device_calibration(self):
        self.store.data['left_stick'].update(axis_x=7, axis_y=6, deadzone=23, invert_x=True)
        current = copy.deepcopy(self.store.data)
        for name in core.FACTORY_PRESETS:
            with self.subTest(name=name):
                data = core.factory_preset(name, current)
                self.assertTrue(self.controls.supports_preset(data))
                self.assertTrue(all(data[key]['enabled'] for key in core.CONTROLS))
                for stick in ('left_stick', 'right_stick'):
                    for field in ('axis_x', 'axis_y', 'deadzone', 'invert_x', 'invert_y'):
                        self.assertEqual(data[stick][field], current[stick][field])
                self.assertEqual(data, core.validate(data))

    def test_legacy_config_migrates_without_changing_assignments(self):
        self.stick()
        old = copy.deepcopy(self.store.data)
        self.path.write_text(json.dumps({'info_language': 'RU', core.CONFIG_KEY: old}))
        migrated = core.Settings(self.path)
        self.assertEqual(migrated.data, old)
        self.assertIsNone(migrated.user_preset)
        self.assertTrue(migrated.apply_factory('Echo'))
        self.assertEqual(core.Settings(self.path).user_preset, old)
        self.assertEqual(json.loads(self.path.read_text())['info_language'], 'RU')

    def test_first_factory_archives_current_once_and_loads_user(self):
        self.stick(mode='Latch')
        self.button('r2', effect='ORBIX')
        initial = copy.deepcopy(self.store.data)
        self.assertTrue(self.store.apply_factory('Ambient'))
        self.assertEqual(self.store.user_preset, initial)
        self.assertTrue(self.store.apply_factory('Tape'))
        self.assertEqual(self.store.user_preset, initial)
        self.assertTrue(self.store.load_user())
        self.assertEqual(self.store.data, initial)
        self.assertEqual(core.Settings(self.path).data, initial)

    def test_user_snapshot_is_independent_and_preserved_by_reset(self):
        self.stick()
        self.assertTrue(self.store.save_user())
        saved = copy.deepcopy(self.store.data)
        self.store.data['left_stick']['x'] = 'orbix.rotation'
        self.assertEqual(self.store.user_preset, saved)
        self.store.replace_controls(core.defaults())
        self.assertEqual(core.Settings(self.path).user_preset, saved)
        self.assertTrue(self.store.load_user())
        self.assertEqual(self.store.data, saved)

    def test_preset_confirm_cancel_and_overwrite_are_explicit(self):
        initial = copy.deepcopy(self.store.data)
        self.preset_action('Granular', confirm=False)
        self.assertTrue(self.menu.confirm)
        self.assertEqual(self.store.data, initial)
        self.assertIsNone(self.store.user_preset)
        self.assertFalse(self.path.exists())
        self.menu.handle('B')
        self.assertFalse(self.menu.confirm)
        self.preset_action('Granular')
        self.assertEqual(self.store.user_preset, initial)
        granular = copy.deepcopy(self.store.data)
        self.preset_action('save_user', confirm=False)
        self.menu.handle('B')
        self.assertEqual(self.store.user_preset, initial)
        self.preset_action('save_user')
        self.assertEqual(self.store.user_preset, granular)
        self.assertEqual(core.Settings(self.path).user_preset, granular)
        self.assertEqual(self.bus.writes, [])

    def test_empty_and_unsupported_presets_are_not_applied(self):
        self.preset_action('load_user')
        self.assertFalse(self.menu.confirm)
        self.assertFalse(self.path.exists())
        del self.bus.params['grain.size']
        self.preset_action('Granular')
        self.assertFalse(self.menu.confirm)
        self.assertEqual(self.store.data, core.defaults())
        self.assertFalse(self.path.exists())

    def test_failed_preset_save_rolls_back_active_and_user_slot(self):
        self.stick()
        old = copy.deepcopy(self.store.data)
        self.store.path = Path(self.temp.name) / 'missing/settings.json'
        self.assertFalse(self.store.apply_factory('Granular'))
        self.assertEqual(self.store.data, old)
        self.assertIsNone(self.store.user_preset)
        self.assertTrue(self.store.error)

    def test_user_slot_validation_is_flat_and_rejects_invalid_snapshots(self):
        self.path.write_text(json.dumps({core.CONFIG_KEY: dict(core.defaults(), user_preset={'version': 999})}))
        self.assertIsNone(core.Settings(self.path).user_preset)
        snapshot = dict(core.defaults(), user_preset={'ignore': 'nested metadata'})
        self.path.write_text(json.dumps({core.CONFIG_KEY: dict(core.defaults(), user_preset=snapshot)}))
        loaded = core.Settings(self.path)
        self.assertEqual(loaded.user_preset, core.defaults())
        self.assertNotIn('user_preset', loaded.user_preset)

    def test_applying_preset_releases_active_effect_before_reassignment(self):
        self.button()
        self.controls.button('l2', True)
        self.assertEqual(self.bus.get('delay.mix'), .65)
        self.preset_action('Granular')
        self.assertEqual(self.bus.get('delay.mix'), .5)
        self.assertFalse(self.controls.sources)


if __name__ == '__main__':
    unittest.main()
