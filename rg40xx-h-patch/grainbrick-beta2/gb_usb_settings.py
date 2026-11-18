"""IPHONE / USB AUDIO page in the native SETTINGS list of GrainBrick BETA 2.0.

BETA 2.0 builds SETTINGS from a scrolling list: ControlManager.SETTINGS_PARAMS
(keys, in order) and the renderer rows, extended through
UIEngine.gb_extra_settings_rows. The new key and row are appended LAST, after
the RHYTHM/BLE integration has installed its own, so both lists stay aligned.

Monitoring while recording is native in BETA 2.0 (REC screen), so this page has
no monitor option; the shared engine hooks (gb_usb_audio) route the iPhone
gadget through PipeWire. No ConfigFS access happens unless the user selects
the IPHONE mode. Unsupported engines retain native audio.
"""
import atexit
import copy
import os
import sys
import time

import pygame
from gb_usb_audio import MODES, Monitor, Settings, endpoints, install_engine_hooks
import gb_pipewire

PARAM = 'settings.grainbernik_usb_audio'
LABEL = 'IPHONE / USB AUDIO'
_installed = _attached = False
_runtime = None


class Runtime:
    def __init__(self, controller, monitor=None, settings=None):
        self.controller, self.ui = controller, None
        self.settings = settings or Settings()
        self.monitor = monitor or Monitor()
        self.open, self.index, self.edit = False, 0, False
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
            # The old pw-loopback monitor is not used: BETA 2.0 monitors natively.
            gb_pipewire.stop_monitor()
        self.route_output()

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
            # Force a rescan now: BETA 2.0 caches the output list for 2.5 s.
            self.ui._audio_outputs_last_scan = -10 ** 9
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
        'mode': ('A: EDIT, THEN LEFT/RIGHT. OR HOLD A AND PRESS LEFT/RIGHT. IPHONE: THE CONSOLE IS A USB SOUND CARD FOR THE IPHONE.',
                 'A: ПРАВКА, ЗАТЕМ ВЛЕВО/ВПРАВО. ИЛИ ДЕРЖИТЕ A И ЖМИТЕ ВЛЕВО/ВПРАВО. IPHONE: КОНСОЛЬ - ЗВУКОВАЯ КАРТА ДЛЯ IPHONE.'),
        'output': ('A: ON/OFF. GRAINBRICK PLAYS TO THE HEADPHONES/SPEAKER AND TO THE IPHONE AT THE SAME TIME.',
                   'A: ВКЛ/ВЫКЛ. GRAINBRICK ЗВУЧИТ В НАУШНИКАХ/ДИНАМИКЕ И В IPHONE ОДНОВРЕМЕННО.'),
        'input': ('A: ON/OFF. RECORD OR PLAY THE IPHONE SOUND: SAMPLE > RECORD / LIVE > USB INPUT. MONITORING IS IN THE REC SCREEN.',
                  'A: ВКЛ/ВЫКЛ. ЗВУК IPHONE: SAMPLE > ЗАПИСЬ / LIVE > USB-ВХОД. МОНИТОРИНГ - НА ЭКРАНЕ ЗАПИСИ.'),
        'status': ('A: START OR RESTART THE USB SOUND CARD MODE OF THE CONSOLE.',
                   'A: ЗАПУСТИТЬ ИЛИ ПЕРЕЗАПУСТИТЬ РЕЖИМ USB-ЗВУКОВОЙ КАРТЫ.'),
        'back': ('RETURN TO SETTINGS. CHANGES ARE ALREADY SAVED.', 'НАЗАД В НАСТРОЙКИ. ИЗМЕНЕНИЯ УЖЕ СОХРАНЕНЫ.'),
    }
    INTRO = ('USE THE CONSOLE AS A SOUND CARD FOR THE IPHONE. IPHONE MODE STARTS USB AUDIO BY ITSELF.',
             'КОНСОЛЬ КАК ЗВУКОВАЯ КАРТА ДЛЯ IPHONE. РЕЖИМ IPHONE ВКЛЮЧАЕТ USB-ЗВУК САМ.')

    def status_text(self):
        cfg = self.settings.data
        if cfg['mode'] == MODES[0]:
            return 'OFF'
        if cfg['mode'] == MODES[1]:
            return 'EXTERNAL USB'
        if gadget.starting():
            return 'STARTING...'
        if not gadget.active():
            return 'PRESS A' if gadget.available() else 'NOT INSTALLED'
        if self.connection != 'USB Connected':
            return 'CONNECT IPHONE'
        return 'IPHONE CONNECTED'

    def rows(self):
        cfg = self.settings.data
        onoff = lambda value: 'ON' if value else 'OFF'
        return [('mode', 'MODE', self.SHORT[cfg['mode']]),
                ('output', 'SEND TO IPHONE', onoff(cfg['output'])),
                ('input', 'RECORD FROM IPHONE', onoff(cfg['input'])),
                ('status', 'STATUS', self.status_text()),
                ('back', 'BACK', '')]

    def info(self, language):
        """(title, text) for the native INFO panel."""
        ru = str(language).upper() == 'RU'
        if not self.open:
            return LABEL, self.INTRO[1 if ru else 0]
        return LABEL, self.HELP[self.rows()[self.index][0]][1 if ru else 0]

    def _change(self, key, direction=None):
        """Apply a value change. direction: -1/+1 for MODE; OFF/ON for the toggles."""
        data = copy.deepcopy(self.settings.data)
        if key == 'mode':
            data['mode'] = MODES[(MODES.index(data['mode']) + direction) % len(MODES)]
        elif direction is None:
            data[key] = not data[key]
        else:
            data[key] = direction > 0
        if data == self.settings.data or not self.settings.save(data):
            return
        if key == 'mode':
            if data['mode'] == MODES[2]:
                gadget.start()
            elif gadget.active():
                gb_pipewire.stop_monitor()
                gadget.stop()
        self.last_scan = 0
        self.tick()

    def handle(self, action):
        """Return True when the action was consumed by this page.

        Same contract as the native "Console Controls" of BETA 2.0:
        A enters the page / a field, B leaves, LEFT/RIGHT edit while a field is
        being edited, and A held + LEFT/RIGHT (ADJUST_*) changes a value at once.
        """
        if not self.open:
            if (self.controller.current_tab == 'SETTINGS' and self.controller.current_param == PARAM
                    and action == 'A'
                    and not getattr(self.controller, 'theme_subpage', False)
                    and not getattr(self.controller, 'debug_menu_active', False)
                    and not getattr(self.controller, 'ble_menu_active', False)):
                self.open, self.index, self.edit = True, 0, False
                self.controller.console_edit = False
                self.last_scan = 0
                self.tick()
                return True
            return False
        if action in ('START', 'EXIT', 'QUIT'):
            return False
        if action in ('L', 'R', 'TAB_PREV', 'TAB_NEXT'):
            return True  # tab switching is blocked while the page is open
        key = self.rows()[self.index][0]
        if action == 'B':
            if self.edit:
                self.edit = False
            else:
                self.open = False
        elif self.edit:
            if action in ('LEFT', 'RIGHT', 'ADJUST_LEFT', 'ADJUST_RIGHT'):
                self._change(key, -1 if action.endswith('LEFT') else 1)
            elif action == 'A':
                self.edit = False
            # UP/DOWN keep the focus on the field until A/B ends the edit.
        elif action in ('UP', 'DOWN'):
            self.index = (self.index + (-1 if action == 'UP' else 1)) % len(self.rows())
        elif action in ('ADJUST_LEFT', 'ADJUST_RIGHT'):
            if key in ('mode', 'output', 'input'):
                self._change(key, -1 if action == 'ADJUST_LEFT' else 1)
        elif action == 'A':
            if key == 'back':
                self.open = False
            elif key == 'status':
                if self.settings.data['mode'] == MODES[2]:
                    gadget.start(restart=True)
            elif key == 'mode':
                self.edit = True
            else:
                self._change(key)  # ON/OFF fields toggle directly
        return True

    def draw(self, ui):
        """Subpage on the 1024x768 logical grid, same style as BLUETOOTH MIDI."""
        ru = str(getattr(ui, 'info_language', 'EN')).upper() == 'RU'
        ui.draw_info_window(PARAM, top_y=115, bottom_y=292, left_x=55, right_x=970)
        pygame.draw.line(ui.screen, ui.VERY_DIM, (38, 300), (986, 300), 1)
        ui.text(LABEL, 55, 325, 4, ui.ACCENT)
        pygame.draw.line(ui.screen, ui.VERY_DIM, (55, 381), (969, 381), 1)
        rows = self.rows()
        iphone = self.settings.data['mode'] == MODES[2]
        for i, (key, label, value) in enumerate(rows):
            y = 400 + i * 52
            focused = i == self.index
            disabled = key in ('output', 'input') and not iphone
            color = ui.ACCENT if focused else ui.DIM if disabled else ui.WHITE
            ui.text('>' if focused else ' ', 35, y, 3, ui.ACCENT)
            ui.text(label, 65, y, 3, color)
            shown = value[:20]
            if focused and self.edit:
                shown = '< ' + shown + ' >'
            ui.text(shown, 573, y, 3, color)
        if self.settings.error:
            ui.text('NOT SAVED: CHECK USB CONFIG FILE', 65, 666, 2, ui.ACCENT)
        elif iphone:
            ui.text(self.device[:60], 65, 666, 2, ui.DIM)


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
    names = ('engine.control', 'engine.input', 'ui.renderer')
    modules = [sys.modules.get(n) for n in names]
    if any(m is None for m in modules):
        return False
    control, inputs, renderer = modules
    C, I, U = control.ControlManager, inputs.InputManager, renderer.UIEngine
    needed = (hasattr(C, 'SETTINGS_PARAMS') and hasattr(C, 'handle')
              and all(hasattr(U, x) for x in ('refresh_audio_outputs', 'draw_settings_page',
                                              '_save_settings', '_gb_draw_footer', 'draw_info_window'))
              and hasattr(renderer, 'get_context_info') and hasattr(I, 'poll') and hasattr(I, 'close'))
    if not needed:
        print('GB USB AUDIO: unsupported BETA 2.0 engine; original audio retained', flush=True)
        return False
    if not install_engine_hooks():
        print('GB USB AUDIO: unsupported engine; original audio retained', flush=True)
        return False
    old_init, old_handle, old_ui = C.__init__, C.handle, U.__init__
    old_draw, old_poll, old_close, old_save = U.draw_settings_page, I.poll, I.close, U._save_settings
    old_footer, old_context = U._gb_draw_footer, renderer.get_context_info
    registered = {'done': False}

    def ensure(ui=None):
        """Add the key and row once the RHYTHM/BLE integration has installed its own."""
        if registered['done']:
            return
        if PARAM not in C.SETTINGS_PARAMS:
            C.SETTINGS_PARAMS = list(C.SETTINGS_PARAMS) + [PARAM]
        if ui is not None and not getattr(ui, '_grainbernik_usb_rows', False):
            previous_rows = getattr(ui, 'gb_extra_settings_rows', None)

            def extra_rows(controls, previous_rows=previous_rows):
                rows = list(previous_rows(controls)) if previous_rows is not None else []
                value = Runtime.SHORT.get(_runtime.settings.data['mode'], '>') if _runtime else '>'
                return rows + [(PARAM, LABEL, value)]
            ui.gb_extra_settings_rows = extra_rows
            ui._grainbernik_usb_rows = True
            registered['done'] = True

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
        ensure(self)
        if _runtime and _runtime.open and controls.current_tab != 'SETTINGS':
            _runtime.open = _runtime.edit = False  # another layer switched the tab
        if _runtime and _runtime.open and controls.current_tab == 'SETTINGS':
            _runtime.draw(self)
            return
        return old_draw(self, controls)

    def footer(self, controls, audio_worker):
        if _runtime and _runtime.open and controls.current_tab == 'SETTINGS':
            pygame.draw.line(self.screen, self.VERY_DIM, (38, 702), (986, 702), 1)
            if _runtime.edit:
                items = [('LEFT/RIGHT CHANGE', self.ACCENT), ('A/B DONE', self.DIM)]
            else:
                items = [('D-PAD NAV', self.DIM), ('A EDIT', self.ACCENT),
                         ('A+L/R QUICK', self.DIM), ('B BACK', self.DIM)]
            self.draw_bar_items(items, left=54, right=795)
            return
        return old_footer(self, controls, audio_worker)

    def context(param, *args, **kw):
        if param == PARAM and _runtime:
            language = args[0] if args else kw.get('language', 'EN')
            return _runtime.info(language)
        return old_context(param, *args, **kw)

    def poll(self, *args, **kw):
        result = old_poll(self, *args, **kw)
        if _runtime:
            _runtime.tick()
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

    C.__init__, C.handle = init, handle
    U.__init__, U.draw_settings_page, U._save_settings, U._gb_draw_footer = ui_init, draw, save, footer
    renderer.get_context_info = context
    I.poll, I.close = poll, close
    _attached = True
    return True


def install():
    global _installed
    if _installed or os.environ.get('GRAINBERNIK_USB_AUDIO', '1') == '0':
        return
    old = pygame.init

    def init(*args, **kw):
        _attach()
        return old(*args, **kw)

    pygame.init = init
    atexit.register(lambda: _runtime.close() if _runtime else None)
    _installed = True
