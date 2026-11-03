"""In-app Advanced Settings adapter for the official GrainBrick beta 1.0.

Loaded after button calibration and display scaling, before importing main.
At pygame.init() the embedded engine/UI modules already exist. Only their
public Python classes and ParameterBus are wrapped; no original file or DSP
binary is edited. Unsupported module layouts leave the original app running.
"""
import atexit
import importlib.util
import os
from pathlib import Path
import sys
import time

import pygame

APP = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location('gb_advanced_controls', APP / 'gb_advanced_controls.py')
_core = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_core)
ADVANCED_PARAM = 'settings.grainbernik_advanced'
_installed = False
_attached = False
_runtime = None

# Like the native app, keep parameter names stable and localize its help text.
MESSAGES = {
    'subtitle': ('INDEPENDENT PERFORMANCE CONTROLS', 'НЕЗАВИСИМОЕ УПРАВЛЕНИЕ ЗВУКОМ'),
    'reset_subtitle': ('RESTORES ONLY THESE FOUR CONTROLS', 'СБРОС ТОЛЬКО ЧЕТЫРЁХ НАЗНАЧЕНИЙ'),
    'reset_title': ('RESTORE DEFAULTS?', 'ВЕРНУТЬ НАСТРОЙКИ ПО УМОЛЧАНИЮ?'),
    'transport': ('START: PLAY/STOP   L1/R1: TABS', 'START: ПУСК/СТОП   L1/R1: ВКЛАДКИ'),
    'navigation': ('D-PAD: SELECT/CHANGE   A: OPEN/CHANGE   B: BACK',
                   'КРЕСТОВИНА: ВЫБОР/ПРАВКА   A: ОТКРЫТЬ   B: НАЗАД'),
    'not_saved': ('NOT SAVED - CHECK SETTINGS FILE / STORAGE', 'НЕ СОХРАНЕНО: ПРОВЕРЬТЕ ФАЙЛ НАСТРОЕК И КАРТУ'),
    'footer_select': ('D-PAD SELECT', 'КРЕСТ: ВЫБОР'),
    'footer_change': ('A CHANGE / B BACK', 'A ПРАВКА / B НАЗАД'),
    'footer_open': ('A OPEN', 'A ОТКРЫТЬ'),
    'entry_title': ('ADVANCED SETTINGS', 'РАСШИРЕННЫЕ НАСТРОЙКИ'),
    'entry_help1': ('ASSIGN STICKS AND L2/R2 TO SOUND PARAMETERS.', 'НАЗНАЧЕНИЯ СТИКОВ И L2/R2 ДЛЯ УПРАВЛЕНИЯ ЗВУКОМ.'),
    'entry_help2': ('EACH CONTROL CAN BE ENABLED SEPARATELY.', 'КАЖДЫЙ ОРГАН ВКЛЮЧАЕТСЯ НЕЗАВИСИМО.'),
    'cancel': ('Cancel', 'Отмена'),
    'restore': ('Restore Defaults', 'Вернуть по умолчанию'),
    'presets': ('Presets', 'Пресеты'),
    'factory_title': ('APPLY PRESET?', 'ПРИМЕНИТЬ ПРЕСЕТ?'),
    'save_user_title': ('SAVE CURRENT TO USER?', 'СОХРАНИТЬ ТЕКУЩУЮ В USER?'),
    'load_user_title': ('LOAD USER PRESET?', 'ЗАГРУЗИТЬ ПРЕСЕТ USER?'),
    'preset_subtitle': ('CONTROL ASSIGNMENTS ONLY; SOUND IS UNCHANGED', 'ТОЛЬКО НАЗНАЧЕНИЯ; ЗВУК НЕ МЕНЯЕТСЯ'),
    'archive_subtitle': ('CURRENT SETUP WILL BE SAVED TO EMPTY USER SLOT', 'ТЕКУЩАЯ РАСКЛАДКА СОХРАНИТСЯ В ПУСТОЙ USER'),
    'save_user_subtitle': ('REPLACES THE SAVED USER SLOT', 'ЗАМЕНЯЕТ СОХРАНЁННЫЙ ПОЛЬЗОВАТЕЛЬСКИЙ СЛОТ'),
    'save_current_subtitle': ('SAVES ALL FOUR CONTROLS AND THEIR OPTIONS', 'СОХРАНИТЬ ЧЕТЫРЕ ОРГАНА И ИХ ПАРАМЕТРЫ'),
    'apply_preset': ('Apply Preset', 'Применить пресет'),
    'save_user': ('Save Current', 'Сохранить текущую'),
    'load_user': ('Load User', 'Загрузить свою'),
    'Saved': ('Saved', 'Сохранено'),
    'Empty': ('Empty', 'Пусто'),
    'Unavailable': ('Unavailable', 'Недоступно'),
}
HELP = {
    'stick': ('Assign independent X/Y parameters to this stick. OFF keeps its assignments and native input.',
              'Назначьте параметры X/Y этому стику. OFF сохраняет назначения и штатное управление.'),
    'button': ('Assign one effect to this button with Hold or Toggle. The other three controls stay independent.',
               'Назначьте эффект кнопке с Hold или Toggle. Остальные три органа настраиваются независимо.'),
    'enabled': ('Enable only this control. Switching OFF releases its effect and keeps the selected assignments.',
                'Включает только этот орган. OFF снимает его эффект и сохраняет выбранные назначения.'),
    'x': ('Horizontal movement controls the selected parameter. None leaves this axis unassigned.',
          'Горизонтальное движение управляет выбранным параметром. None отключает назначение оси.'),
    'y': ('Vertical movement controls the selected parameter. None leaves this axis unassigned.',
          'Вертикальное движение управляет выбранным параметром. None отключает назначение оси.'),
    'options': ('Open deadzone, sensitivity, inversion, Spring/Latch, smoothing and physical axis settings.',
                'Мёртвая зона, чувствительность, инверсия, Spring/Latch, сглаживание и физические оси.'),
    'deadzone': ('Ignore motion near center. Default 12%. Increase if the stick drifts while released.',
                 'Не учитывает движения около центра. По умолчанию 12%. Увеличьте при дрейфе стика.'),
    'sensitivity': ('At 100%, full deflection changes half the parameter range from the starting value.',
                    'При 100% полный ход меняет половину диапазона параметра относительно начального значения.'),
    'invert_x': ('Reverse the direction of horizontal parameter changes.', 'Меняет направление изменения параметра по горизонтали.'),
    'invert_y': ('Reverse the direction of vertical parameter changes.', 'Меняет направление изменения параметра по вертикали.'),
    'Spring': ('Return smoothly to the gesture starting value when the stick is released.',
               'При отпускании стика плавно возвращает значение к началу жеста.'),
    'Latch': ('Keep the last value when centered. Disable or enter a non-performance screen to release it.',
              'В центре сохраняет последнее значение. OFF или вход в меню снимает воздействие.'),
    'Hold': ('The effect is active while held. Release restores the values from before activation.',
             'Эффект действует при удержании. Отпускание возвращает значения до включения.'),
    'Toggle': ('Press to activate, press again to restore. Opening a menu also releases the effect.',
               'Нажатие включает, повторное возвращает исходные значения. Вход в меню снимает эффект.'),
    'smoothing': ('Response time in milliseconds. Higher values make movement gentler; 0 disables extra smoothing.',
                  'Время отклика в миллисекундах. Больше — плавнее; 0 отключает дополнительное сглаживание.'),
    'physical_axis': ('SDL axis index. Default left 0/1, right 2/3. Reserved analog trigger axes are ignored.',
                      'Номер оси SDL. Обычно слева 0/1, справа 2/3. Оси аналоговых курков не используются.'),
    'Freeze': ('Native Motion Hold freezes small audio fragments, not a spectral freeze.',
               'Штатный Motion Hold удерживает короткие фрагменты звука; это не спектральная заморозка.'),
    'Reverse': ('Uses native Motion Reverse inside the audio flow; does not reverse the sample file.',
                'Штатный Motion Reverse меняет движение звука; файл сэмпла не разворачивается.'),
    'Delay Throw': ('Temporarily sets delay mix and feedback. Restores both on deactivation.',
                    'Временно меняет mix и feedback задержки. При выключении возвращает оба значения.'),
    'Reverb Wash': ('Temporarily increases reverb mix, size and decay. Restores all three on deactivation.',
                    'Временно увеличивает mix, size и decay реверберации. При выключении возвращает значения.'),
    'Pitch Drop': ('Enables grain processing and lowers pitch by one octave. Restores the previous sound afterward.',
                   'Включает гранулятор и понижает высоту на октаву. Затем возвращает прежнее звучание.'),
    'Bypass': ('Bypass delay, reverb, shimmer, tape, compressor and EQ; preserve sample/grain playback.',
               'Отключает delay, reverb, shimmer, tape, компрессор и EQ; воспроизведение продолжается.'),
    'ORBIX': ('Enables native ORBIX in Hold/Toggle mode. Use START for playback; previous enable state is restored.',
              'Включает ORBIX в Hold/Toggle. START управляет воспроизведением. Прежнее состояние возвращается.'),
    'None': ('No extra effect or input capture. Enable the control and select an assignment to use it.',
             'Без дополнительного эффекта и перехвата ввода. Для работы включите орган и выберите назначение.'),
    'reset': ('Requires confirmation. Reset these four assignments only; keep native sound and app settings.',
              'Требует подтверждения. Сброс только четырёх назначений; звук и штатные настройки сохраняются.'),
    'back': ('Return one menu level. Assignments are already saved. L1/R1 changes main tabs.',
             'Назад на один уровень. Назначения уже сохранены. L1/R1 переключают основные вкладки.'),
    'cancel': ('Keep current assignments and cancel this operation.', 'Сохранить текущие назначения и отменить операцию.'),
    'restore': ('Turn all four controls OFF and restore their default assignments and options.',
                'Выключить четыре органа и вернуть их назначения и параметры по умолчанию.'),
    'presets': ('Five factory layouts and one User slot. Changes require confirmation; saved User is preserved.',
                'Пять готовых раскладок и слот User. Выбор пресета не перезаписывает занятый User.'),
    'Granular': ('L: Position/Size; R: Pitch/Density. L2 Freeze, R2 Reverse. Spring, 70% sensitivity.',
                 'Слева Position/Size; справа Pitch/Density. L2 Freeze, R2 Reverse. Spring, чувствительность 70%.'),
    'Ambient': ('L: Position/Spray; R: Reverb/Shimmer. L2 Freeze, R2 Reverb Wash. Gentle 180 ms response.',
                'Слева Position/Spray; справа Reverb/Shimmer. L2 Freeze, R2 Reverb Wash. Плавный отклик 180 мс.'),
    'Echo': ('L: Delay Time/Feedback; R: Delay/Reverb Mix. L2 Delay Throw, R2 Reverb Wash.',
             'Слева Delay Time/Feedback; справа Delay/Reverb Mix. L2 Delay Throw, R2 Reverb Wash.'),
    'Tape': ('L: Saturation/Wow; R: Pitch/Flutter. L2 Pitch Drop, R2 Bypass. Sensitivity 40%.',
             'Слева Saturation/Wow; справа Pitch/Flutter. L2 Pitch Drop, R2 Bypass. Чувствительность 40%.'),
    'ORBIX Play': ('L: Rotation/Gravity; R: Bounce/Reverb. L2 ORBIX Toggle, R2 Reverb Wash. START plays/stops.',
                   'Слева Rotation/Gravity; справа Bounce/Reverb. L2 ORBIX Toggle, R2 Reverb Wash. START: пуск/стоп.'),
    'load_user': ('Load your saved four-control setup. Empty slot cannot be loaded. Changes need confirmation.',
                  'Загрузить свою раскладку четырёх органов. Пустой слот недоступен. Нужны подтверждение и A.'),
    'save_user': ('Save all four current assignments and options into User. Confirm before replacing the saved slot.',
                  'Сохранить четыре текущих назначения и параметры в User. Замена слота требует подтверждения.'),
}


def _localized(ui, table, key):
    return table[key][1 if str(getattr(ui, 'info_language', 'EN')).upper() == 'RU' else 0]


def _log(message):
    print('GB ADVANCED: ' + message, flush=True)


class Runtime:
    def __init__(self, controller, settings_path):
        self.controller = controller
        self.settings = _core.Settings(settings_path)
        self.controls = _core.Controls(controller.parameters, self.settings)
        self.menu = _core.Menu(self.settings, self.controls)
        self.ui = None
        self.input = None
        self.claimed_buttons = set()
        self.focused = True
        self.excluded_axes = set()
        try:
            import json
            data = json.loads((APP / 'gb_buttons.json').read_text(encoding='utf-8'))
            self.excluded_axes = {int(x) for x in data.get('trigger_axes', {}).values()}
        except (OSError, ValueError, TypeError):
            pass

    def performance(self):
        ui = self.ui
        return (self.focused and self.menu.page is None
                and self.controller.current_tab in ('GRAIN', 'FX', 'TAPE', 'VISUAL')
                and not getattr(ui, 'info_mode', False)
                and not getattr(ui, 'button_map_active', False)
                and not getattr(self.input, 'capture_mode', False))

    def events(self, events):
        result = []
        for event in events:
            kind = event.type
            if kind in (pygame.QUIT, getattr(pygame, 'JOYDEVICEREMOVED', -1)):
                self.controls.cancel()
                self.focused = False
            elif kind == getattr(pygame, 'WINDOWFOCUSLOST', -2):
                self.focused = False
                self.controls.cancel()
            elif kind == getattr(pygame, 'WINDOWFOCUSGAINED', -3):
                self.focused = True
            if kind in (pygame.JOYBUTTONDOWN, pygame.JOYBUTTONUP) and event.button in (10, 11):
                button = event.button
                name = 'l2' if button == 10 else 'r2'
                down = kind == pygame.JOYBUTTONDOWN
                # Do not steal buttons from the app's own rebinding overlay.
                eligible = (self.performance() and self.settings.data[name]['enabled']
                            and self.settings.data[name]['effect'] in self.controls.effect_choices()
                            and self.settings.data[name]['effect'] is not None)
                if down and eligible:
                    self.claimed_buttons.add(button)
                    self.controls.button(name, True)
                    continue
                if not down and button in self.claimed_buttons:
                    self.claimed_buttons.discard(button)
                    self.controls.button(name, False, self.performance())
                    continue
            # Sticks have no native GrainBrick binding. Leave disabled and
            # unassigned axes untouched, including calibrated analog triggers.
            if kind == pygame.JOYAXISMOTION and self.performance():
                if any(cfg['enabled'] and cfg[axis] is not None
                       and event.axis == cfg['axis_' + axis]
                       and event.axis not in self.excluded_axes
                       for name in ('left_stick', 'right_stick')
                       for cfg in (self.settings.data[name],) for axis in ('x', 'y')):
                    continue
            result.append(event)
        return result

    def tick(self, input_manager):
        self.input = input_manager
        axes = {}
        joy = input_manager.joy
        try:
            if self.performance() and any(self.settings.data[n]['enabled']
                                           for n in ('left_stick', 'right_stick')):
                axes = {i: joy.get_axis(i) for i in range(joy.get_numaxes())}
        except pygame.error:
            self.controls.cancel()
        self.controls.tick(axes, time.monotonic(), self.performance(), self.excluded_axes)

    def handle(self, action):
        if self.menu.page is not None:
            if action in ('L', 'R', 'TAB_PREV', 'TAB_NEXT'):
                # Assignments are saved on edit. Leave the overlay before
                # switching the native tab so it cannot keep capturing input.
                self.controls.cancel()
                self.menu.page, self.menu.confirm, self.menu.pending = None, False, None
                self.controller.change_tab(-1 if action in ('L', 'TAB_PREV') else 1)
                return True
            if action in ('EXIT', 'START'):
                self.controls.cancel()
                return False
            self.menu.handle(action)
            return True
        if (self.controller.current_tab == 'SETTINGS'
                and self.controller.current_param == ADVANCED_PARAM
                and action in ('A', 'RIGHT')):
            self.menu.open()
            if self.ui:
                self.ui.info_mode = False
            return True
        return False

    def draw(self, ui):
        screen = ui.screen
        pygame.draw.rect(screen, ui.BG, (0, 88, ui.WIDTH, ui.HEIGHT - 132))
        page = self.menu.page
        title = ('ADVANCED SETTINGS' if page == 'root' else _localized(ui, MESSAGES, 'presets').upper()
                 if page == 'presets' else self.menu.LABELS[page.split('.')[0]].upper())
        subtitle = 'subtitle'
        if self.menu.confirm:
            kind = self.menu.pending[0] if self.menu.pending is not None else 'reset'
            title = _localized(ui, MESSAGES, kind + '_title')
            if kind == 'factory':
                title += ' ' + self.menu.pending[1].upper()
            subtitle = ('reset_subtitle' if kind == 'reset' else
                        ('save_user_subtitle' if self.settings.user_preset is not None else 'save_current_subtitle')
                        if kind == 'save_user' else
                        'archive_subtitle' if kind == 'factory' and self.settings.user_preset is None
                        else 'preset_subtitle')
        elif page.endswith('.options'):
            title += ' / OPTIONS'
        ui.text(title, 54, 112, scale=3, color=ui.ACCENT)
        ui.text(_localized(ui, MESSAGES, subtitle),
                54, 165, scale=2, color=ui.DIM)
        ui.text(_localized(ui, MESSAGES, 'transport'), 54, 196, scale=2, color=ui.DIM)
        rows = self.menu.rows()
        start = max(0, min(self.menu.index - 5, len(rows) - 7))
        for i, (key, label, value) in enumerate(rows[start:start + 7], start):
            y = 233 + (i - start) * 54
            disabled = (page == 'root' and key in _core.CONTROLS
                        and not self.settings.data[key]['enabled'])
            if page == 'presets':
                disabled = value == 'Unavailable' or key == 'load_user' and self.settings.user_preset is None
            if page not in ('root', 'presets') and not self.menu.confirm:
                disabled = not self.settings.data[page.split('.')[0]]['enabled'] and key != 'back'
            selected = i == self.menu.index
            color = ui.ACCENT if selected else ui.DIM if disabled else ui.WHITE
            if selected:
                ui.text('>', 32, y, scale=3, color=ui.ACCENT)
            if key in MESSAGES and (self.menu.confirm or key in ('presets', 'load_user', 'save_user')):
                label = _localized(ui, MESSAGES, key)
            if value in ('Saved', 'Empty', 'Unavailable'):
                value = _localized(ui, MESSAGES, value)
            ui.text(label.upper(), 64, y, scale=3, color=color)
            ui.text(str(value).upper(), 540, y, scale=3, color=color)
        if len(rows) > 7:
            ui.text('%d/%d' % (self.menu.index + 1, len(rows)), 894, 170, scale=2, color=ui.DIM)
        help_text = self.help_text(ui)
        for line, y in zip(ui._wrap_info_text(help_text, max_chars=64), (606, 632)):
            ui.text(line, 54, y, scale=2, color=ui.DIM)
        if self.settings.error:
            ui.text(_localized(ui, MESSAGES, 'not_saved'), 54, 658, scale=2, color=ui.ACCENT)
        ui.text(_localized(ui, MESSAGES, 'navigation'), 54, 680, scale=2, color=ui.DIM)

    def help_text(self, ui):
        key = self.menu.rows()[self.menu.index][0]
        if key == 'apply_preset':
            key = self.menu.pending[1]
        if self.menu.page == 'root' and key in _core.CONTROLS:
            key = 'stick' if key.endswith('stick') else 'button'
        elif key == 'mode':
            key = self.settings.data[self.menu.page.split('.')[0]]['mode']
        elif key in ('axis_x', 'axis_y'):
            key = 'physical_axis'
        elif key == 'effect':
            key = self.settings.data[self.menu.page]['effect'] or 'None'
        return _localized(ui, HELP, key if key in HELP else 'None')


def _attach():
    global _attached
    if _attached:
        return True
    modules = [sys.modules.get(name) for name in ('engine.control', 'engine.input', 'ui.renderer')]
    if any(mod is None for mod in modules):
        return False
    control_mod, input_mod, renderer_mod = modules
    ControlManager, InputManager, UIEngine = control_mod.ControlManager, input_mod.InputManager, renderer_mod.UIEngine
    if not all(hasattr(ControlManager, key) for key in ('SETTINGS_PARAMS', 'handle')):
        _log('unsupported engine, original controls retained')
        return False
    original_control_init = ControlManager.__init__
    original_handle = ControlManager.handle
    original_ui_init = UIEngine.__init__
    original_draw_settings = UIEngine.draw_settings_page
    original_save_settings = UIEngine._save_settings
    original_footer_hint = UIEngine.footer_hint
    original_poll = InputManager.poll
    original_close = InputManager.close

    def control_init(self, *args, **kwargs):
        global _runtime
        original_control_init(self, *args, **kwargs)
        _runtime = Runtime(self, UIEngine.SETTINGS_PATH)

    def handle(self, action, value=None):
        if _runtime is not None and _runtime.controller is self and _runtime.handle(action):
            return
        result = original_handle(self, action, value)
        if _runtime is not None and not _runtime.performance():
            _runtime.controls.cancel()
        return result

    def ui_init(self, *args, **kwargs):
        original_ui_init(self, *args, **kwargs)
        if _runtime is not None:
            _runtime.ui = self

    def draw_settings(self, controls):
        runtime = _runtime
        if runtime is not None and runtime.menu.page is not None:
            runtime.draw(self)
            return
        original_draw_settings(self, controls)
        selected = controls.current_param == ADVANCED_PARAM
        color = self.ACCENT if selected else self.WHITE
        if selected:
            # Supply the contextual help for the new native settings row.
            pygame.draw.rect(self.screen, self.BG, (0, 88, self.WIDTH, 200))
            self.text(_localized(self, MESSAGES, 'entry_title'), 54, 122, scale=4, color=self.ACCENT)
            self.text(_localized(self, MESSAGES, 'entry_help1'), 54, 196, scale=3, color=self.WHITE)
            self.text(_localized(self, MESSAGES, 'entry_help2'), 54, 232, scale=3, color=self.WHITE)
            self.text('>', 34, 678, scale=3, color=color)
        self.text('ADVANCED SETTINGS', 64, 678, scale=3, color=color)
        self.text('>', 480, 678, scale=3, color=color)

    def save_settings(self):
        # Native settings changes must not erase our nested configuration.
        preserved = None
        if _runtime is not None:
            try:
                preserved = _runtime.settings._read()
            except (OSError, ValueError, TypeError):
                pass
        result = original_save_settings(self)
        if _runtime is not None:
            _runtime.settings.save(preserved)
        return result

    def footer_hint(self, message):
        entry = (_runtime is not None and _runtime.controller.current_tab == 'SETTINGS'
                 and _runtime.controller.current_param == ADVANCED_PARAM)
        if _runtime is not None and (_runtime.menu.page is not None or entry):
            if message in ('UP/DOWN', 'B / A CHANGE'):
                key = ('footer_select' if message == 'UP/DOWN' else
                       'footer_change' if _runtime.menu.page is not None else 'footer_open')
                message = _localized(self, MESSAGES, key)
        return original_footer_hint(self, message)

    def poll(self, *args, **kwargs):
        if _runtime is not None:
            _runtime.input = self
        result = original_poll(self, *args, **kwargs)
        if _runtime is not None:
            _runtime.tick(self)
            if any(action in ('EXIT', 'QUIT') for action, value in result):
                # Unwind before main saves its sound state on shutdown.
                _runtime.controls.cancel()
            if _runtime.menu.page is not None:
                # SELECT is intercepted directly by main before ControlManager.
                result = [(action, value) for action, value in result if action != 'SELECT']
        return result

    def close(self):
        if _runtime is not None:
            _runtime.controls.cancel()
        return original_close(self)

    ControlManager.SETTINGS_PARAMS = list(ControlManager.SETTINGS_PARAMS) + [ADVANCED_PARAM]
    ControlManager.__init__, ControlManager.handle = control_init, handle
    UIEngine.__init__, UIEngine.draw_settings_page, UIEngine._save_settings = ui_init, draw_settings, save_settings
    UIEngine.footer_hint = footer_hint
    InputManager.poll, InputManager.close = poll, close
    _attached = True
    _log('attached to native Settings / ParameterBus')
    return True


def install():
    global _installed
    if _installed or os.environ.get('GRAINBERNIK_ADVANCED', '1') == '0':
        return
    original_init = pygame.init
    original_get = pygame.event.get

    def init(*args, **kwargs):
        _attach()
        return original_init(*args, **kwargs)

    def get(*args, **kwargs):
        events = original_get(*args, **kwargs)
        return _runtime.events(events) if _runtime is not None else events

    pygame.init, pygame.event.get = init, get
    atexit.register(lambda: _runtime.controls.cancel() if _runtime is not None else None)
    _installed = True
    _log('installed; waiting for native engine initialization')
