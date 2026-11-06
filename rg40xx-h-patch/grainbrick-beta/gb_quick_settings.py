"""Quick audio/presets with adjacent detailed pages and USB hotplug detection."""
import copy
import sys
import time

import pygame
import gb_advanced as advanced
import gb_usb_settings as usb
from gb_usb_audio import MODES

AUDIO = 'settings.grainbernik_quick_audio'
CONTROLS = 'settings.grainbernik_quick_controls'
OTHER = 'settings.grainbernik_other'
ROOT = [AUDIO, usb.PARAM, CONTROLS, advanced.ADVANCED_PARAM, OTHER]
_installed = _attached = False
_runtime = None


def physical(identifier):
    name = str(identifier).lower()
    return name not in ('internal', 'default', 'grainbernik_usb_gadget') and not any(
        word in name for word in ('uac2', 'gadget'))


class Runtime:
    def __init__(self, controller, native_params):
        self.controller, self.ui = controller, None
        self.other_params = [p for p in native_params if p not in
                             ('settings.audio_output', usb.PARAM, advanced.ADVANCED_PARAM)]
        self.more, self.audio, self.quick_presets = False, False, False
        self.index, self.last_scan = 0, 0
        self.connected = None
        self.capture_id, self.capture_label = None, 'NO USB INPUT'
        self.owned_output = None
        controller.SETTINGS_PARAMS = list(ROOT)

    def tick(self):
        if self.ui is None or time.monotonic() - self.last_scan < .75:
            return
        self.last_scan = time.monotonic()
        inputs, outputs = sys.modules['engine.audio_inputs'], sys.modules['engine.audio_devices']
        try:
            captures = getattr(inputs, '_grainbernik_native_captures', inputs.available_usb_captures)()
            sinks = getattr(outputs, '_grainbernik_native_outputs', outputs.available_outputs)()
        except (OSError, RuntimeError):
            return
        captures = [c for c in captures if physical(c['card_id'])]
        sinks = [s for s in sinks if physical(s[0])]
        ids = {c['card_id'] for c in captures} | {s[0] for s in sinks}
        new = ids - (self.connected or set())
        previous_capture = self.capture_id
        if captures:
            chosen = next((c for c in captures if c['card_id'] in new), None)
            chosen = chosen or next((c for c in captures if c['card_id'] == self.capture_id), captures[0])
            self.capture_id, self.capture_label = chosen['card_id'], chosen.get('label', chosen['card_id'])
        else:
            self.capture_id, self.capture_label = None, 'NO USB INPUT'
        cfg = usb._runtime.settings if usb._runtime else None
        iphone = cfg is not None and cfg.data['mode'] == MODES[2]
        if new and not iphone:
            chosen_sink = next((s for s in sinks if s[0] in new), None)
            if chosen_sink:
                self.ui.audio_output_id = chosen_sink[0]
                self.owned_output = chosen_sink[0]
                self.ui.refresh_audio_outputs()
            elif not physical(self.ui.audio_output_id) and self.ui.audio_output_id != 'internal':
                self.ui.audio_output_id = 'internal'
                self.ui.refresh_audio_outputs()
            if cfg is not None:
                data = copy.deepcopy(cfg.data)
                data['mode'] = MODES[1]
                cfg.save(data)
                if usb.gadget.active():
                    usb.gadget.stop()
            print('GB AUDIO: USB detected: %s; input=%s' % (', '.join(sorted(new)), self.capture_label), flush=True)
        if self.owned_output and self.owned_output not in ids:
            if self.ui.audio_output_id == self.owned_output:
                self.ui.audio_output_id = 'internal'
                self.ui.refresh_audio_outputs()
            self.owned_output = None
        if previous_capture and not self.capture_id:
            print('GB AUDIO: USB input disconnected; built-in output retained', flush=True)
        self.connected = ids

    def params(self, more):
        self.more = more
        self.controller.SETTINGS_PARAMS = list(self.other_params if more else ROOT)
        self.controller.settings_param_index = 0 if more else ROOT.index(OTHER)

    def audio_rows(self):
        rt = usb._runtime
        iphone = rt and rt.settings.data['mode'] == MODES[2]
        return [('mode', 'CONNECTION', 'IPHONE' if iphone else 'AUTO'),
                ('input', 'INPUT', 'IPHONE' if iphone else self.capture_label),
                ('output', 'OUTPUT', self.ui.audio_output_label()),
                ('back', 'BACK', '')]

    def handle(self, action):
        if self.quick_presets and advanced._runtime:
            menu = advanced._runtime.menu
            if menu.page is None:
                self.quick_presets = False
            elif menu.page == 'presets' and not menu.confirm and (
                    action == 'B' or action in ('A', 'RIGHT') and menu.rows()[menu.index][0] == 'back'):
                menu.page = None
                self.quick_presets = False
                return True
        if self.audio:
            if action in ('EXIT', 'QUIT', 'START'):
                return False
            if action in ('L', 'R', 'TAB_PREV', 'TAB_NEXT'):
                self.audio = False
                return False
            key = self.audio_rows()[self.index][0]
            if action == 'B' or key == 'back' and action in ('A', 'RIGHT'):
                self.audio = False
            elif action in ('UP', 'DOWN'):
                self.index = (self.index + (-1 if action == 'UP' else 1)) % len(self.audio_rows())
            elif key == 'mode' and action in ('A', 'LEFT', 'RIGHT') and usb._runtime:
                rt = usb._runtime
                data = copy.deepcopy(rt.settings.data)
                data['mode'] = (MODES[1] if self.capture_id else MODES[0]) if data['mode'] == MODES[2] else MODES[2]
                if rt.settings.save(data):
                    if data['mode'] == MODES[2]:
                        usb.gadget.start()
                    elif usb.gadget.active():
                        usb.gadget.stop()
                    rt.last_scan = 0
                    rt.tick()
            return True
        if self.controller.current_tab != 'SETTINGS':
            if self.more:
                self.params(False)
            return False
        if self.more:
            if action == 'B':
                self.params(False)
                return True
            return False
        if action not in ('A', 'RIGHT'):
            return False
        key = self.controller.current_param
        if key == AUDIO:
            self.audio, self.index = True, 0
            self.ui.info_mode = False
        elif key == CONTROLS and advanced._runtime:
            advanced._runtime.menu.open()
            advanced._runtime.menu.page = 'presets'
            self.quick_presets = True
            self.ui.info_mode = False
        elif key == OTHER:
            self.params(True)
        else:
            return False
        return True

    def draw(self, ui, controller):
        if self.audio:
            title, help_text = 'AUDIO', 'USB INPUT AND OUTPUT ARE DETECTED AUTOMATICALLY.'
            rows = self.audio_rows()
            index = self.index
        else:
            title = 'OTHER SETTINGS' if self.more else 'SETTINGS'
            help_text = 'QUICK SETUP OR DETAILED OPTIONS FOR EACH SECTION.'
            if self.more:
                values = {'settings.info_language': ('INFO LANGUAGE', ui.info_language),
                          'settings.save_params_on_exit': ('SAVE ON EXIT', 'ON' if ui.save_params_on_exit else 'OFF'),
                          'settings.button_mapping': ('BUTTON MAPPING', '>'),
                          'settings.reset_sound_params': ('RESET SOUND', '>')}
            else:
                values = {AUDIO: ('AUDIO', self.capture_label if self.capture_id else 'AUTO'),
                          usb.PARAM: ('AUDIO / ADVANCED', '>'),
                          CONTROLS: ('CONTROLS', 'PRESETS'),
                          advanced.ADVANCED_PARAM: ('CONTROLS / ADVANCED', '>'),
                          OTHER: ('OTHER SETTINGS', '>')}
            rows = [(key, *values[key]) for key in controller.SETTINGS_PARAMS]
            index = controller.settings_param_index
        pygame.draw.rect(ui.screen, ui.BG, (0, 88, ui.WIDTH, ui.HEIGHT - 132))
        ui.text(title, 54, 112, scale=4, color=ui.ACCENT)
        ru = str(ui.info_language).upper() == 'RU'
        if ru:
            help_text = ('USB-ВХОД И ВЫХОД ОПРЕДЕЛЯЮТСЯ АВТОМАТИЧЕСКИ.' if self.audio else
                         'БЫСТРАЯ НАСТРОЙКА И ПОДРОБНЫЕ ПАРАМЕТРЫ РЯДОМ.')
        for line, y in zip(ui._wrap_info_text(help_text, max_chars=64), (176, 202)):
            ui.text(line, 54, y, scale=2, color=ui.DIM)
        pygame.draw.line(ui.screen, ui.VERY_DIM, (38, 240), (ui.WIDTH - 38, 240))
        for i, (key, label, value) in enumerate(rows):
            y = 282 + i * 64
            color = ui.ACCENT if i == index else ui.WHITE
            if i == index:
                ui.text('>', 34, y, scale=3, color=color)
            ui.text(label, 64, y, scale=3, color=color)
            ui.text(str(value).upper()[:25], 610, y, scale=2, color=color)
        ui.text('A: OPEN / CHANGE   B: BACK', 54, ui.HEIGHT - 64, scale=2, color=ui.DIM)


def _attach():
    global _attached
    if _attached:
        return True
    if not usb._attached or not advanced._attached:
        return False
    control, inputs, renderer = [sys.modules[n] for n in ('engine.control', 'engine.input', 'ui.renderer')]
    C, I, U = control.ControlManager, inputs.InputManager, renderer.UIEngine
    native_params = list(C.SETTINGS_PARAMS)
    old_init, old_ui, old_handle = C.__init__, U.__init__, C.handle
    old_draw, old_poll = U.draw_settings_page, I.poll
    audio_inputs = sys.modules['engine.audio_inputs']
    old_captures = audio_inputs.available_usb_captures

    def ordered_captures(*a, **kw):
        result = old_captures(*a, **kw)
        if _runtime and _runtime.capture_id:
            return sorted(result, key=lambda c: c['card_id'] != _runtime.capture_id)
        return result

    for name, module in list(sys.modules.items()):
        if module is not None and (name == 'main' or name.startswith('engine.')):
            if getattr(module, 'available_usb_captures', None) is old_captures:
                module.available_usb_captures = ordered_captures

    def init(self, *a, **kw):
        global _runtime
        old_init(self, *a, **kw)
        _runtime = Runtime(self, native_params)

    def ui_init(self, *a, **kw):
        old_ui(self, *a, **kw)
        if _runtime:
            _runtime.ui = self
            _runtime.tick()

    def handle(self, action, value=None):
        if _runtime and _runtime.controller is self and _runtime.handle(action):
            return
        return old_handle(self, action, value)

    def draw(self, controller):
        if _runtime and not (usb._runtime and usb._runtime.open) and not (
                advanced._runtime and advanced._runtime.menu.page is not None):
            return _runtime.draw(self, controller)
        return old_draw(self, controller)

    def poll(self, *a, **kw):
        result = old_poll(self, *a, **kw)
        if _runtime:
            _runtime.tick()
            if _runtime.audio:
                result = [(k, v) for k, v in result if k != 'SELECT']
        return result

    # Put manual playback-device selection in the adjacent Audio / Advanced
    # page, rather than mixing it into Other Settings.
    old_rows, old_usb_handle = usb.Runtime.rows, usb.Runtime.handle
    usb.Runtime.HELP['native_output'] = ('CHOOSE A PLAYBACK DEVICE MANUALLY. NEW USB DEVICES ARE SELECTED AUTOMATICALLY.',
                                       'РУЧНОЙ ВЫБОР ВЫХОДА. НОВЫЕ USB-УСТРОЙСТВА ВЫБИРАЮТСЯ САМИ.')

    def audio_rows(self):
        rows = old_rows(self)
        rows.insert(-1, ('native_output', 'PLAYBACK OUTPUT', self.ui.audio_output_label() if self.ui else 'AUTO'))
        return rows

    def audio_handle(self, action):
        if self.open and self.rows()[self.index][0] == 'native_output' and action in ('A', 'LEFT', 'RIGHT'):
            self.ui.step_audio_output(-1 if action == 'LEFT' else 1)
            return True
        return old_usb_handle(self, action)

    usb.Runtime.rows, usb.Runtime.handle = audio_rows, audio_handle
    C.__init__, C.handle = init, handle
    U.__init__, U.draw_settings_page = ui_init, draw
    I.poll = poll
    _attached = True
    return True


def install():
    global _installed
    if _installed:
        return
    old_init = pygame.init

    def init(*a, **kw):
        advanced._attach()
        usb._attach()
        _attach()
        return old_init(*a, **kw)

    pygame.init = init
    _installed = True
