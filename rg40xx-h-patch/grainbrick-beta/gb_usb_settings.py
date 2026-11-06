"""USB Audio settings in GrainBrick's native Settings page (1.0.1).

Uses the same Pygame initialization hook as Advanced Settings. No activation
of ConfigFS is performed from the UI; unsupported engines retain native audio.
"""
import atexit
import copy
import os
import sys
import time

import pygame
from gb_usb_audio import CONFIG, MODES, Monitor, Settings, endpoints, install_engine_hooks
import gb_pipewire

PARAM = 'settings.grainbernik_usb_audio'
_installed = _attached = False
_runtime = None


class Runtime:
    def __init__(self, controller, monitor=None, settings=None):
        self.controller, self.ui = controller, None
        self.settings = settings or Settings()
        self.monitor = monitor or Monitor()
        self.open, self.index = False, 0
        self.last_scan = 0
        self.connection, self.device = 'Unknown', 'Not Probed'
        self.owned_output = False
        self.last_output = None
        # A previous iPhone session may have left PipeWire's default on UAC2.
        self._restore_pending = True

    def tick(self):
        now = time.monotonic()
        if now - self.last_scan < 0.75:
            return
        self.last_scan = now
        self.connection, self.device = self.monitor.status(self.settings.data)
        if self.settings.data['mode'] == MODES[2] and not gadget.auto_tried:
            gadget.auto_tried = True
            gadget.start()
        if gb_pipewire.available():
            gb_pipewire.follow_headphone_jack()
            if self.connection != 'USB Connected' or self.settings.data['mode'] != MODES[2]:
                gb_pipewire.stop_monitor()
        self.route_output()

    def toggle_monitor(self):
        """SELECT while recording from the iPhone: input monitoring on/off."""
        data = copy.deepcopy(self.settings.data)
        data['monitor'] = not data['monitor']
        self.settings.save(data)
        if data['monitor']:
            gb_pipewire.start_monitor()
        else:
            gb_pipewire.stop_monitor()
        print('GB USB AUDIO: input monitoring', 'ON' if data['monitor'] else 'OFF', flush=True)

    def route_output(self):
        if self.ui is None:
            return
        cfg = self.settings.data
        enabled = cfg['mode'] == MODES[2] and cfg['output'] and self.connection == 'USB Connected'
        if enabled:
            try:
                endpoints(self.monitor.system, cfg)
            except RuntimeError:
                enabled = False
        selected = getattr(self.ui, 'audio_output_id', 'internal')
        if enabled:
            self._restore_pending = True
            if not self.owned_output:
                # "default" may currently resolve to the USB gadget on ROCKNIX.
                # Preserve explicit external device IDs, but not that alias.
                if selected != 'grainbernik_usb_gadget':
                    data = copy.deepcopy(cfg)
                    data['previous_output'] = ('internal' if selected in ('', 'default') else selected)
                    if not self.settings.save(data):
                        return
                self.owned_output = True
            self.ui.audio_output_id = 'grainbernik_usb_gadget'
        else:
            if self.owned_output or selected == 'grainbernik_usb_gadget':
                previous = cfg.get('previous_output', 'internal')
                self.ui.audio_output_id = ('internal' if previous in
                    ('', 'default', 'grainbernik_usb_gadget') else previous)
                self.owned_output = False
            if self._restore_pending and gb_pipewire.available():
                # Repair only stale UAC2/gb_both defaults; preserve unrelated
                # system-selected sinks. Native output ID is handled above.
                gb_pipewire.restore_builtin_default()
                self._restore_pending = False
        desired = self.ui.audio_output_id
        if desired != self.last_output:
            self.ui.refresh_audio_outputs()
            self.last_output = desired

    def close(self):
        if self.ui and (self.owned_output or self.ui.audio_output_id == 'grainbernik_usb_gadget'):
            previous = self.settings.data.get('previous_output', 'internal')
            self.ui.audio_output_id = ('internal' if previous in
                ('', 'default', 'grainbernik_usb_gadget') else previous)
            self.owned_output = False
        if gb_pipewire.available():
            gb_pipewire.restore_builtin_default()
        self.open = False

    # ---------------------------------------------------------------- page
    SHORT = {MODES[0]: 'OFF', MODES[1]: 'USB INTERFACE', MODES[2]: 'IPHONE'}
    HELP = {
        'mode': ('IPHONE: THE CONSOLE BECOMES A USB SOUND CARD FOR THE IPHONE. USB INTERFACE: AN EXTERNAL USB SOUND CARD.',
                 'IPHONE: КОНСОЛЬ СТАНОВИТСЯ ЗВУКОВОЙ КАРТОЙ ДЛЯ IPHONE. USB-ИНТЕРФЕЙС: ВНЕШНЯЯ USB-КАРТА.'),
        'output': ('GRAINBRICK PLAYS TO THE HEADPHONES/SPEAKER AND TO THE IPHONE AT THE SAME TIME.',
                   'GRAINBRICK ЗВУЧИТ В НАУШНИКАХ/ДИНАМИКЕ И В IPHONE ОДНОВРЕМЕННО.'),
        'input': ('RECORD THE IPHONE SOUND: SAMPLE > Y RECORD > USB AUDIO.',
                  'ЗАПИСЬ ЗВУКА С IPHONE: SAMPLE > Y ЗАПИСЬ > USB AUDIO.'),
        'monitor': ('HEAR THE IPHONE IN THE HEADPHONES WHILE RECORDING. SELECT ALSO TOGGLES IT DURING RECORDING.',
                    'СЛЫШАТЬ IPHONE В НАУШНИКАХ ВО ВРЕМЯ ЗАПИСИ. SELECT ТОЖЕ ПЕРЕКЛЮЧАЕТ ВО ВРЕМЯ ЗАПИСИ.'),
        'status': ('A: START OR RESTART THE USB SOUND CARD MODE OF THE CONSOLE.',
                   'A: ЗАПУСТИТЬ ИЛИ ПЕРЕЗАПУСТИТЬ РЕЖИМ USB-ЗВУКОВОЙ КАРТЫ.'),
        'back': ('RETURN TO SETTINGS. CHANGES ARE ALREADY SAVED.', 'НАЗАД В НАСТРОЙКИ. ИЗМЕНЕНИЯ УЖЕ СОХРАНЕНЫ.'),
    }

    def status_text(self):
        cfg = self.settings.data
        if cfg['mode'] == MODES[0]:
            return 'OFF'
        if cfg['mode'] == MODES[1]:
            return 'USE SAMPLE > USB AUDIO'
        if gadget.starting():
            return 'STARTING...'
        if not gadget.active():
            return 'NOT STARTED - PRESS A' if gadget.available() else 'NOT INSTALLED'
        if self.connection != 'USB Connected':
            return 'CONNECT IPHONE (USB-C)'
        return 'IPHONE CONNECTED'

    def rows(self):
        cfg = self.settings.data
        onoff = lambda value: 'ON' if value else 'OFF'
        return [('mode', 'MODE', self.SHORT[cfg['mode']]),
                ('output', 'SEND TO IPHONE', onoff(cfg['output'])),
                ('input', 'RECORD FROM IPHONE', onoff(cfg['input'])),
                ('monitor', 'MONITOR WHILE RECORDING', onoff(cfg['monitor'])),
                ('status', 'STATUS', self.status_text()),
                ('back', 'BACK', '')]

    def handle(self, action):
        if not self.open:
            if (self.controller.current_tab == 'SETTINGS' and self.controller.current_param == PARAM
                    and action in ('A', 'RIGHT')):
                self.open = True
                self.index = 0
                if self.ui:
                    self.ui.info_mode = False
                self.last_scan = 0
                self.tick()
                return True
            return False
        if action in ('START', 'EXIT', 'QUIT'):
            return False
        if action in ('L', 'R', 'TAB_PREV', 'TAB_NEXT'):
            self.open = False
            return False
        key = self.rows()[self.index][0]
        if action == 'B' or key == 'back' and action in ('A', 'RIGHT'):
            self.open = False
        elif action in ('UP', 'DOWN'):
            self.index = (self.index + (-1 if action == 'UP' else 1)) % len(self.rows())
        elif key == 'status' and action == 'A':
            if self.settings.data['mode'] == MODES[2]:
                gadget.start(restart=True)
        elif action in ('LEFT', 'RIGHT', 'A') and key in ('mode', 'output', 'input', 'monitor'):
            data = copy.deepcopy(self.settings.data)
            if key == 'mode':
                step = -1 if action == 'LEFT' else 1
                data['mode'] = MODES[(MODES.index(data['mode']) + step) % len(MODES)]
            else:
                data[key] = not data[key]
            if self.settings.save(data):
                if key == 'mode':
                    if data['mode'] == MODES[2]:
                        gadget.start()
                    elif gadget.active():
                        gb_pipewire.stop_monitor()
                        gadget.stop()
                if key == 'monitor' and not data['monitor']:
                    gb_pipewire.stop_monitor()
                self.last_scan = 0
                self.tick()
        return True

    def draw(self, ui):
        # Native renderer uses a 1024x768 virtual canvas on 1.0.1.
        w, h = ui.WIDTH, ui.HEIGHT
        ru = str(getattr(ui, 'info_language', 'EN')).upper() == 'RU'
        pygame.draw.rect(ui.screen, ui.BG, (0, 88, w, h - 132))
        ui.text('IPHONE / USB AUDIO', 54, 111, scale=4, color=ui.ACCENT)
        rows = self.rows()
        key = rows[self.index][0]
        help_text = self.HELP[key][1 if ru else 0]
        for line, y in zip(ui._wrap_info_text(help_text, max_chars=64), (165, 191)):
            ui.text(line, 54, y, scale=2, color=ui.DIM)
        pygame.draw.line(ui.screen, ui.VERY_DIM, (38, 232), (w - 38, 232))
        for i, (row, label, value) in enumerate(rows):
            y = 258 + i * 50
            iphone = self.settings.data['mode'] == MODES[2]
            disabled = row in ('output', 'input', 'monitor') and not iphone
            color = ui.ACCENT if i == self.index else ui.DIM if disabled else ui.WHITE
            if i == self.index:
                ui.text('>', 34, y, scale=3, color=color)
            ui.text(label, 64, y, scale=3 if len(label) < 20 else 2, color=color)
            ui.text(value[:28], 600, y, scale=2, color=color)
        if self.settings.error:
            ui.text('NOT SAVED: CHECK USB CONFIG FILE', 54, h - 100, scale=2, color=ui.ACCENT)
        ui.text('КРЕСТ: ВЫБОР   A: ИЗМЕНИТЬ   B: НАЗАД' if ru else 'D-PAD: SELECT   A: CHANGE   B: BACK',
                54, h - 64, scale=2, color=ui.DIM)


class _Gadget:
    """Start/stop the UAC2 USB sound card mode from the app (no SSH needed)."""
    ON, OFF = '/storage/uac2/uac2-on.sh', '/storage/uac2/uac2-off.sh'
    UDC = '/sys/kernel/config/usb_gadget/grainbernik/UDC'

    def __init__(self):
        self._thread = None
        self.auto_tried = False

    def available(self):
        return os.path.isfile(self.ON)

    def active(self):
        try:
            with open(self.UDC, encoding='utf-8') as stream:
                return bool(stream.read().strip())
        except OSError:
            return False

    def starting(self):
        return self._thread is not None and self._thread.is_alive()

    def _run(self, script):
        import subprocess
        try:
            result = subprocess.run(['sh', script], capture_output=True, text=True, timeout=30)
            print('GB USB AUDIO: %s -> %s' % (os.path.basename(script), result.returncode), flush=True)
        except (OSError, subprocess.SubprocessError) as exc:
            print('GB USB AUDIO: %s failed: %r' % (script, exc), flush=True)

    def _spawn(self, script):
        import threading
        if self.starting() or not os.path.isfile(script):
            return
        self._thread = threading.Thread(target=self._run, args=(script,), name='gb-uac2', daemon=True)
        self._thread.start()

    def start(self, restart=False):
        if restart or not self.active():
            self._spawn(self.ON)

    def stop(self):
        self._spawn(self.OFF)


gadget = _Gadget()


def _attach():
    global _attached
    if _attached:
        return True
    modules = [sys.modules.get(n) for n in ('engine.control', 'engine.input', 'ui.renderer')]
    if any(m is None for m in modules):
        return False
    control, inputs, renderer = modules
    C, I, U = control.ControlManager, inputs.InputManager, renderer.UIEngine
    supported = {'settings.info_language', 'settings.save_params_on_exit', 'settings.audio_output',
                 'settings.button_mapping', 'settings.reset_sound_params', 'settings.grainbernik_advanced'}
    if not hasattr(C, 'SETTINGS_PARAMS') or any(p not in supported for p in C.SETTINGS_PARAMS):
        return False
    if not all(hasattr(U, x) for x in ('refresh_audio_outputs', 'draw_settings_page', '_save_settings')):
        return False
    if not install_engine_hooks():
        print('GB USB AUDIO: unsupported engine; original audio retained', flush=True)
        return False
    old_init, old_handle, old_ui = C.__init__, C.handle, U.__init__
    old_draw, old_poll, old_close, old_save = U.draw_settings_page, I.poll, I.close, U._save_settings

    def init(self, *args, **kw):
        global _runtime
        old_init(self, *args, **kw)
        _runtime = Runtime(self)

    def ui_init(self, *args, **kw):
        old_ui(self, *args, **kw)
        if _runtime:
            _runtime.ui = self
            _runtime.tick()

    def handle(self, action, value=None):
        if _runtime and _runtime.controller is self and _runtime.handle(action):
            return
        return old_handle(self, action, value)

    def draw(self, controls):
        if _runtime and _runtime.open:
            _runtime.draw(self)
            return
        old_draw(self, controls)
        advanced = sys.modules.get('gb_advanced')
        if advanced and advanced._runtime and advanced._runtime.menu.page is not None:
            return
        # The native page has five fixed rows. Fit all seven above its footer
        # while retaining the original help/header, values and pixel font.
        pygame.draw.rect(self.screen, self.BG, (0, 374, self.WIDTH, self.HEIGHT - 438))
        values = {
            'settings.info_language': ('INFO LANGUAGE', self.info_language),
            'settings.save_params_on_exit': ('SAVE PARAMS ON EXIT', 'ON' if self.save_params_on_exit else 'OFF'),
            'settings.audio_output': ('AUDIO OUTPUT LIVE', self.audio_output_label()),
            'settings.button_mapping': ('BUTTON MAPPING', '>'),
            'settings.reset_sound_params': ('RESET SOUND PARAMS', '>'),
            'settings.grainbernik_advanced': ('STICKS & BUTTONS', '>'),
            PARAM: ('IPHONE / USB AUDIO', Runtime.SHORT.get(_runtime.settings.data['mode'], '>') if _runtime else '>')}
        for index, param in enumerate(C.SETTINGS_PARAMS):
            label, value = values[param]
            color = self.ACCENT if controls.current_param == param else self.WHITE
            y = 388 + index * 46
            if controls.current_param == param:
                self.text('>', 34, y, scale=3, color=color)
            self.text(label, 64, y, scale=3, color=color)
            self.text(str(value), 480, y, scale=3, color=color)
        if controls.current_param == PARAM:
            pygame.draw.rect(self.screen, self.BG, (0, 88, self.WIDTH, 200))
            ru = str(getattr(self, 'info_language', 'EN')).upper() == 'RU'
            self.text('IPHONE / USB AUDIO', 54, 122, scale=4, color=self.ACCENT)
            self.text('КОНСОЛЬ КАК ЗВУКОВАЯ КАРТА ДЛЯ IPHONE.' if ru else 'USE THE CONSOLE AS A SOUND CARD FOR IPHONE.',
                      54, 196, scale=3, color=self.WHITE)
            self.text('РЕЖИМ IPHONE ВКЛЮЧАЕТ USB-ЗВУК САМ.' if ru else 'IPHONE MODE STARTS USB AUDIO BY ITSELF.',
                      54, 232, scale=2, color=self.DIM)

    def poll(self, *args, **kw):
        result = old_poll(self, *args, **kw)
        if _runtime:
            _runtime.tick()
            if gb_pipewire.available() and gb_pipewire.recording() and any(a == 'SELECT' for a, v in result):
                _runtime.toggle_monitor()
                result = [(a, v) for a, v in result if a != 'SELECT']
            if _runtime.open:
                result = [(a, v) for a, v in result if a != 'SELECT']
        return result

    def close(self):
        if _runtime:
            _runtime.close()
        return old_close(self)

    def save(self):
        # Never persist our transient selection in native settings.json.
        selected = self.audio_output_id
        if selected == 'grainbernik_usb_gadget':
            previous = _runtime.settings.data.get('previous_output', 'internal') if _runtime else 'internal'
            self.audio_output_id = ('internal' if previous in
                ('', 'default', 'grainbernik_usb_gadget') else previous)
        try:
            return old_save(self)
        finally:
            self.audio_output_id = selected

    C.SETTINGS_PARAMS = list(C.SETTINGS_PARAMS) + [PARAM]
    C.__init__, C.handle = init, handle
    U.__init__, U.draw_settings_page, U._save_settings = ui_init, draw, save
    I.poll, I.close = poll, close
    _attached = True
    return True


def install():
    global _installed
    if _installed or os.environ.get('GRAINBERNIK_USB_AUDIO', '1') == '0':
        return
    old = pygame.init

    def init(*args, **kw):
        # Attach Advanced first so its wrapping does not cover our overlay.
        advanced = sys.modules.get('gb_advanced')
        if advanced and getattr(advanced, '_installed', False) and hasattr(advanced, '_attach'):
            advanced._attach()
        _attach()
        return old(*args, **kw)

    pygame.init = init
    atexit.register(lambda: _runtime.close() if _runtime else None)
    _installed = True
