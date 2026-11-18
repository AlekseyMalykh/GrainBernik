"""Advanced Settings ("STICKS & BUTTONS") for the official GrainBrick BETA 2.0.

Adds, in the native SETTINGS list, a page that assigns the two sticks, L2/R2 and
the L3/R3 clicks to sound parameters / effects, plus factory and user presets.
Everything is expanded for BETA 2.0: GRAIN 2/3 randomisation, ORBIX Rings,
OSCILLATOR, RHYTHM tempo and LIVE input/master levels (all parameter ids are
checked against the running ParameterBus; unknown ones are hidden).

BETA 2.0 differences from the 1.0.1 adapter:
  * Buttons are taken from the engine's own AutoKeyAdapter output (virtual
    buttons L2=10, R2=11, L3=15, R3=16), so no SDL mapping guessing is needed.
  * The page follows the "Console Controls": A enters / edits, B leaves,
    LEFT/RIGHT change while editing, A held + LEFT/RIGHT is a quick change.
  * The SETTINGS row is registered lazily through gb_settings_rows so the key
    list and the renderer rows stay aligned with RHYTHM / BLE / USB rows.
No original file is edited; unsupported layouts keep the app untouched.
"""
import atexit
import importlib.util
import os
from pathlib import Path
import sys
import time

import pygame

APP = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location('gb_advanced2_controls', APP / 'gb_advanced2_controls.py')
_core = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_core)
import gb_settings_rows

PARAM = 'settings.grainbernik_advanced'
LABEL = 'STICKS & BUTTONS'
_installed = False
_attached = False
_runtime = None
# Virtual buttons produced by engine.autokey.AutoKeyAdapter.
VIRTUAL_BUTTONS = {10: 'l2', 11: 'r2', 15: 'l3', 16: 'r3'}

HELP = {
    'stick': ('Assign independent X/Y parameters to this stick. OFF keeps its assignments and native input.',
              'Назначьте параметры X/Y этому стику. OFF сохраняет назначения и штатное управление.'),
    'button': ('Assign one effect to this button with Hold or Toggle. The other controls stay independent.',
               'Назначьте эффект кнопке с Hold или Toggle. Остальные органы настраиваются независимо.'),
    'click': ('Stick click (press the stick in). Toggle is recommended: click on, click again off.',
              'Нажатие на стик. Рекомендуется Toggle: нажали — включено, ещё раз — выключено.'),
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
    'reset': ('Requires confirmation. Reset these six assignments only; keep native sound and app settings.',
              'Требует подтверждения. Сброс только шести назначений; звук и штатные настройки сохраняются.'),
    'back': ('Return one menu level. Assignments are already saved. L1/R1 changes main tabs.',
             'Назад на один уровень. Назначения уже сохранены. L1/R1 переключают основные вкладки.'),
    'cancel': ('Keep current assignments and cancel this operation.', 'Сохранить текущие назначения и отменить операцию.'),
    'restore': ('Turn all six controls OFF and restore their default assignments and options.',
                'Выключить шесть органов и вернуть их назначения и параметры по умолчанию.'),
    'presets': ('Six factory layouts and one User slot. Changes require confirmation; saved User is preserved.',
                'Шесть готовых раскладок и слот User. Выбор пресета не перезаписывает занятый User.'),
    'Granular': ('L Pos/Size, R Pitch/Density. L2 Freeze, R2 Reverse, L3 Octave -, R3 Octave + (steps).',
                 'L Pos/Size, R Pitch/Density. L2 Freeze, R2 Reverse, L3 октава вниз, R3 октава вверх.'),
    'Ambient': ('L Pos/Spray, R Reverb/Shimmer. L2 Freeze, R2 Reverb Wash, L3 Shimmer Burst, R3 Bypass.',
                'L Pos/Spray, R Reverb/Shimmer. L2 Freeze, R2 Reverb Wash, L3 Shimmer, R3 Bypass.'),
    'Texture': ('L Size/Spray, R Density/Roam. L2 Grain Burst, R2 Freeze, L3 Reverse, R3 Stutter.',
                'L Size/Spray, R Density/Roam. L2 Grain Burst, R2 Freeze, L3 Reverse, R3 Stutter.'),
    'Echo': ('L Time/Feedback, R Delay/Reverb Mix. L2 Delay Throw, R2 Reverb Wash, L3 Freeze, R3 Bypass.',
             'L Time/Feedback, R Delay/Reverb Mix. L2 Delay Throw, R2 Reverb Wash, L3 Freeze, R3 Bypass.'),
    'Tape': ('L Saturation/Wow, R Pitch/Flutter. L2 Pitch Drop, R2 Lo-Fi, L3 Reverse, R3 Bypass.',
             'L Saturation/Wow, R Pitch/Flutter. L2 Pitch Drop, R2 Lo-Fi, L3 Reverse, R3 Bypass.'),
    'ORBIX Play': ('L Rotation/Gravity, R Bounce/Reverb. L2 ORBIX, R2 Reverb Wash, L3 Freeze, R3 Shimmer.',
                   'L Rotation/Gravity, R Bounce/Reverb. L2 ORBIX, R2 Reverb Wash, L3 Freeze, R3 Shimmer.'),
    'Octave Up': ('Enables grain processing and raises pitch by one octave. Restores the previous sound afterward.',
                  'Включает гранулятор и повышает высоту на октаву. Затем возвращает прежнее звучание.'),
    'Shimmer Burst': ('Temporarily raises shimmer mix and feedback for a bright halo. Restores both afterward.',
                      'Временно усиливает shimmer mix и feedback — яркий ореол. Затем возвращает значения.'),
    'Grain Burst': ('Temporarily raises grain density and spray for a dense cloud. Restores both afterward.',
                    'Временно увеличивает плотность и разброс зёрен — плотное облако. Затем возвращает значения.'),
    'Lo-Fi': ('Enables tape and 8-bit mode for a crunchy sound. Restores the previous state afterward.',
              'Включает tape и 8-бит для грязного звука. Затем возвращает прежнее состояние.'),
    'Octave +': ('Each press transposes grain pitch one octave up and keeps it. Limited to the pitch range.',
                 'Каждое нажатие поднимает высоту зёрен на октаву и оставляет её. В пределах диапазона.'),
    'Octave -': ('Each press transposes grain pitch one octave down and keeps it. Limited to the pitch range.',
                 'Каждое нажатие опускает высоту зёрен на октаву и оставляет её. В пределах диапазона.'),
    'Step': ('Step action: every press changes the value once; nothing is restored on release.',
             'Шаговое действие: каждое нажатие меняет значение один раз; при отпускании не возвращается.'),
    'Stutter': ('Native Motion jump and chaos make the playback position skip. Restores afterward.',
                'Штатные Motion jump и chaos заставляют позицию прыгать. Затем значения возвращаются.'),
    'load_user': ('Load your saved control setup. Empty slot cannot be loaded. Changes need confirmation.',
                  'Загрузить свою раскладку органов. Пустой слот недоступен. Нужны подтверждение и A.'),
    'save_user': ('Save all current assignments and options into User. Confirm before replacing the saved slot.',
                  'Сохранить все текущие назначения и параметры в User. Замена слота требует подтверждения.'),
}


HELP.update({
    'Scatter': ('GRAIN 2/3: spreads pitch, size and timing of the grains while held. Restores afterward.',
                'GRAIN 2/3: разбрасывает высоту, размер и тайминг зёрен. Затем возвращает значения.'),
    'Reverse Grains': ('GRAIN 2/3: plays every grain backwards while held. Restores afterward.',
                       'GRAIN 2/3: все зёрна играют задом наперёд. Затем возвращает значения.'),
    'Rings Bloom': ('ORBIX Rings: open, bright and long ring-out. Needs ORBIX on. Restores afterward.',
                    'ORBIX Rings: открытый яркий долгий звон. Нужен включённый ORBIX. Затем возврат.'),
    'Rings Damp': ('ORBIX Rings: strong damping and dark tone to choke the resonance. Restores afterward.',
                   'ORBIX Rings: сильное затухание и тёмный тон — глушит резонанс. Затем возврат.'),
    'Rings Detune': ('ORBIX Rings: detunes the resonator and widens stereo. Restores afterward.',
                     'ORBIX Rings: расстраивает резонатор и расширяет стерео. Затем возврат.'),
    'Osc On': ('OSCILLATOR: switches the oscillator on while held. Restores the previous state.',
               'OSCILLATOR: включает осциллятор на время нажатия. Затем прежнее состояние.'),
    'Osc Drive': ('OSCILLATOR: on, with high drive. Restores afterward.',
                  'OSCILLATOR: включён, сильный драйв. Затем возврат.'),
    'Osc FM': ('OSCILLATOR: on, with strong cross modulation. Restores afterward.',
               'OSCILLATOR: включён, сильная кросс-модуляция. Затем возврат.'),
    'Slow Down': ('RHYTHM: tempo -20 BPM while held; the original tempo returns on release.',
                  'RHYTHM: темп -20 BPM при удержании; при отпускании возвращается прежний.'),
    'Speed Up': ('RHYTHM: tempo +20 BPM while held; the original tempo returns on release.',
                 'RHYTHM: темп +20 BPM при удержании; при отпускании возвращается прежний.'),
    'Tempo +5': ('RHYTHM: each press raises the tempo by 5 BPM and keeps it.',
                 'RHYTHM: каждое нажатие добавляет 5 BPM и оставляет темп.'),
    'Tempo -5': ('RHYTHM: each press lowers the tempo by 5 BPM and keeps it.',
                 'RHYTHM: каждое нажатие убавляет 5 BPM и оставляет темп.'),
    'Input Cut': ('LIVE: input level to minimum while held (kills feedback). Restores afterward.',
                  'LIVE: уровень входа на минимум при удержании (гасит наводку). Затем возврат.'),
    'Input Boost': ('LIVE: input level +6 dB while held. Restores afterward.',
                    'LIVE: уровень входа +6 dB при удержании. Затем возврат.'),
    'Mute Out': ('Master output to silence while held (panic mute). Restores afterward.',
                 'Мастер-выход в тишину при удержании (паник-мьют). Затем возврат.'),
    'Rhythm': ('L Pos/Size, R Density/Pitch. L2/R2 Slow/Speed Up, L3/R3 Tempo -5/+5.',
               'L Pos/Size, R Density/Pitch. L2/R2 медленнее/быстрее, L3/R3 темп -5/+5.'),
    'Rings': ('L Structure/Brightness, R Damping/Position. L2 Bloom, R2 Damp, L3 ORBIX, R3 Detune.',
              'L Structure/Brightness, R Damping/Position. L2 Bloom, R2 Damp, L3 ORBIX, R3 Detune.'),
    'Oscillator': ('L Blend/Drive, R X-Mod/Dry-Wet. L2 Osc FM, R2 Osc Drive, L3 Osc On, R3 Bypass.',
                   'L Blend/Drive, R X-Mod/Dry-Wet. L2 Osc FM, R2 Osc Drive, L3 Osc On, R3 Bypass.'),
    'Live': ('L Position/Input level, R Density/Spray. L2 Input Cut, R2 Mute Out, L3 Freeze, R3 Grain Burst.',
             'L Position/Input level, R Density/Spray. L2 Input Cut, R2 Mute Out, L3 Freeze, R3 Grain Burst.'),
    'Grain 2/3': ('L Size/Timing random, R Pitch spread/Reverse chance. L2 Scatter, R2 Reverse Grains, L3 Freeze, R3 Octave +.',
                  'L Size/Timing random, R Pitch spread/Reverse chance. L2 Scatter, R2 Reverse Grains, L3 Freeze, R3 Octave +.'),
    'presets': ('Eleven factory layouts and one User slot. Changes require confirmation; saved User is preserved.',
                'Одиннадцать готовых раскладок и слот User. Выбор пресета не перезаписывает занятый User.'),
    'entry': ('Assign the sticks, L2/R2 and L3/R3 clicks to sound. A opens, B goes back.',
              'Стики, L2/R2 и нажатия L3/R3 для звука. A открывает, B возвращает.'),
})

HELP.update({
    'Granular': ('L Position/Size, R Pitch/Density. L2 Freeze, R2 Reverse, L3 Octave -, R3 Octave + (steps).',
                 'L: позиция и размер, R: высота и плотность. L2 заморозка, R2 реверс, L3 октава вниз, R3 октава вверх.'),
    'Ambient': ('L Position/Spray, R Reverb/Shimmer. L2 Freeze, R2 Reverb Wash, L3 Shimmer Burst, R3 Bypass.',
                'L: позиция и разброс, R: реверб и шиммер. L2 заморозка, R2 Reverb Wash, L3 Shimmer Burst, R3 Bypass.'),
    'Texture': ('L Size/Spray, R Density/Roam speed. L2 Grain Burst, R2 Freeze, L3 Reverse, R3 Stutter.',
                'L: размер и разброс, R: плотность и скорость Roam. L2 Grain Burst, R2 заморозка, L3 реверс, R3 Stutter.'),
    'Echo': ('L Delay time/Feedback, R Delay/Reverb mix. L2 Delay Throw, R2 Reverb Wash, L3 Freeze, R3 Bypass.',
             'L: время и обратная связь задержки, R: микс задержки и ревербa. L2 Delay Throw, R2 Reverb Wash, L3 заморозка, R3 Bypass.'),
    'Tape': ('L Saturation/Wow, R Pitch/Flutter. L2 Pitch Drop, R2 Lo-Fi, L3 Reverse, R3 Bypass.',
             'L: насыщение и wow, R: высота и flutter. L2 Pitch Drop, R2 Lo-Fi, L3 реверс, R3 Bypass.'),
    'ORBIX Play': ('L Rotation/Gravity, R Bounce/Reverb. L2 ORBIX, R2 Reverb Wash, L3 Freeze, R3 Shimmer Burst.',
                   'L: вращение и гравитация, R: отскок и реверб ORBIX. L2 ORBIX, R2 Reverb Wash, L3 заморозка, R3 Shimmer Burst.'),
    'Rhythm': ('RHYTHM: L Position/Size, R Density/Pitch. L2 Slow Down, R2 Speed Up (held), L3 Tempo -5, R3 Tempo +5 (steps).',
               'RHYTHM: L позиция и размер, R плотность и высота. L2 темп медленнее, R2 быстрее (пока держишь), L3 темп -5, R3 темп +5 (шаг).'),
    'Rings': ('ORBIX Rings: L Structure/Brightness, R Damping/Position. L2 Rings Bloom, R2 Rings Damp, L3 ORBIX on/off, R3 Rings Detune.',
              'ORBIX Rings: L структура и яркость, R затухание и позиция. L2 Rings Bloom, R2 Rings Damp, L3 вкл/выкл ORBIX, R3 Rings Detune.'),
    'Oscillator': ('OSCILLATOR: L Blend/Drive, R X-Mod/Dry-Wet. L2 Osc FM, R2 Osc Drive, L3 Osc On, R3 Bypass.',
                   'OSCILLATOR: L смесь и драйв, R кросс-модуляция и dry/wet. L2 Osc FM, R2 Osc Drive, L3 Osc On, R3 Bypass.'),
    'Live': ('LIVE: L Position/Input level, R Density/Spray. L2 Input Cut, R2 Mute Out, L3 Freeze, R3 Grain Burst.',
             'LIVE: L позиция и уровень входа, R плотность и разброс. L2 Input Cut, R2 Mute Out, L3 заморозка, R3 Grain Burst.'),
    'Grain 2/3': ('GRAIN 2/3: L Size random/Timing random, R Pitch spread/Reverse chance. L2 Scatter, R2 Reverse Grains, L3 Freeze, R3 Octave +.',
                  'GRAIN 2/3: L случайность размера и тайминга, R разброс высоты и шанс реверса. L2 Scatter, R2 Reverse Grains, L3 заморозка, R3 Octave +.'),
    'presets': ('Eleven factory layouts and a User slot. The active preset is shown; changing any assignment makes it User.',
                'Одиннадцать готовых раскладок и слот User. Активный пресет показан; любое изменение назначений делает его User.'),
    'entry': ('Assign the sticks, L2/R2 and L3/R3 clicks to sound. A opens, B goes back.',
              'Стики, L2/R2 и клики L3/R3 для управления звуком. A открывает, B возвращает.'),
    'None': ('No extra effect or input capture. Enable the control and select an assignment to use it.',
             'Без дополнительного эффекта и перехвата ввода. Для работы включите орган и выберите назначение.'),
})

# Row labels / values in Russian (parameter and effect names stay as in the app).
LABELS_RU = {
    'Left Stick': 'Левый стик', 'Right Stick': 'Правый стик', 'L2 Button': 'Кнопка L2',
    'R2 Button': 'Кнопка R2', 'L3 Click': 'Клик L3', 'R3 Click': 'Клик R3',
    'Preset': 'Пресет', 'Reset to Defaults': 'Сброс', 'Back': 'Назад', 'Enabled': 'Включено',
    'X Effect': 'Эффект X', 'Y Effect': 'Эффект Y', 'Stick Options': 'Настройки стика',
    'Effect': 'Эффект', 'Mode': 'Режим', 'Deadzone': 'Мёртвая зона', 'Sensitivity': 'Чувствит.',
    'Invert X': 'Инверсия X', 'Invert Y': 'Инверсия Y', 'Return Mode': 'Возврат',
    'Smoothing': 'Сглаживание', 'Physical X Axis': 'Ось X (физ.)', 'Physical Y Axis': 'Ось Y (физ.)',
    'Cancel': 'Отмена', 'Restore Defaults': 'Вернуть по умолч.', 'Apply Preset': 'Применить',
    'Save User': 'Сохранить свой', 'Load User': 'Загрузить свой',
}
VALUES_RU = {'ON': 'ВКЛ', 'OFF': 'ВЫКЛ', 'ACTIVE': 'АКТИВЕН', 'Empty': 'Пусто', 'Saved': 'Сохранён',
             'Unavailable': 'Недоступно', 'None': 'Нет', 'User': 'Свой'}
FOOTER_RU = {'D-PAD NAV': 'КРЕСТ: ВЫБОР', 'A EDIT': 'A ПРАВКА', 'A TOGGLE': 'A ВКЛ/ВЫКЛ', 'A OPEN': 'A ОТКРЫТЬ',
             'A+L/R QUICK': 'A+L/R БЫСТРО', 'B BACK': 'B НАЗАД', 'LEFT/RIGHT CHANGE': 'ВЛЕВО/ВПРАВО: ИЗМЕНИТЬ',
             'A/B DONE': 'A/B ГОТОВО', 'A CONFIRM': 'A ПОДТВЕРДИТЬ', 'B CANCEL': 'B ОТМЕНА'}

# Localized strings for the confirmation pages.
MESSAGES = {
    'reset_title': ('RESTORE DEFAULTS?', 'ВЕРНУТЬ НАСТРОЙКИ ПО УМОЛЧАНИЮ?'),
    'factory_title': ('APPLY PRESET?', 'ПРИМЕНИТЬ ПРЕСЕТ?'),
    'save_user_title': ('SAVE CURRENT TO USER?', 'СОХРАНИТЬ ТЕКУЩУЮ В USER?'),
    'load_user_title': ('LOAD USER PRESET?', 'ЗАГРУЗИТЬ ПРЕСЕТ USER?'),
    'not_saved': ('NOT SAVED: CHECK SETTINGS FILE', 'НЕ СОХРАНЕНО: ПРОВЕРЬТЕ ФАЙЛ НАСТРОЕК'),
    'preset': ('PRESET', 'ПРЕСЕТ'),
    'presets_title': ('PRESETS', 'ПРЕСЕТЫ'),
}


def _lang(ui):
    return 1 if str(getattr(ui, 'info_language', 'EN')).upper() == 'RU' else 0


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
        self.claimed = set()      # virtual buttons whose DOWN we consumed
        self.excluded_axes = set()

    # --- state -------------------------------------------------------------
    @property
    def open(self):
        return self.menu.page is not None

    def _blocked(self):
        ui, c = self.ui, self.controller
        return (getattr(ui, 'info_mode', False) or getattr(ui, 'button_map_active', False)
                or getattr(self.input, 'capture_mode', False)
                or getattr(c, 'ble_menu_active', False)
                or getattr(c, 'project_name_editing', False))

    def performance(self):
        return (not self.open and self.controller.current_tab in ('GRAIN', 'FX', 'TAPE', 'VISUAL')
                and not self._blocked())

    def claims(self, name):
        """L3/R3 are owned on every screen while ON (so a stick click never
        switches tabs); L2/R2 only on sound tabs and only with an effect."""
        cfg = self.settings.data.get(name)
        if not cfg or not cfg['enabled']:
            return False
        if name in ('l3', 'r3'):
            return not (getattr(self.ui, 'button_map_active', False)
                        or getattr(self.input, 'capture_mode', False))
        return (self.performance() and cfg['effect'] is not None
                and cfg['effect'] in self.controls.effect_choices())

    # --- input -------------------------------------------------------------
    def filter_events(self, events):
        """Consume owned buttons from AutoKeyAdapter's virtual event list."""
        result = []
        for event in events:
            kind = getattr(event, 'type', None)
            if kind == pygame.QUIT:
                self.controls.cancel()
            number = getattr(event, 'button', None)
            name = VIRTUAL_BUTTONS.get(number) if kind in (pygame.JOYBUTTONDOWN, pygame.JOYBUTTONUP) else None
            if name is not None:
                if kind == pygame.JOYBUTTONDOWN and self.claims(name):
                    self.claimed.add(number)
                    self.controls.button(name, True, self.performance())
                    continue
                if kind == pygame.JOYBUTTONUP and number in self.claimed:
                    self.claimed.discard(number)
                    self.controls.button(name, False, self.performance())
                    continue
            result.append(event)
        return result

    def tick(self, input_manager):
        self.input = input_manager
        axes = {}
        joy = getattr(input_manager, 'joy', None)
        try:
            if (joy is not None and self.performance()
                    and any(self.settings.data[n]['enabled'] for n in ('left_stick', 'right_stick'))):
                axes = {i: joy.get_axis(i) for i in range(joy.get_numaxes())}
        except pygame.error:
            self.controls.cancel()
        auto = getattr(input_manager, 'auto_key', None)
        if auto is not None and getattr(auto, 'mode', '') == 'mapped_raw':
            self.excluded_axes = set(getattr(auto, 'raw_axes', {}))
        self.controls.tick(axes, time.monotonic(), self.performance(), self.excluded_axes)

    def handle(self, action):
        if self.open:
            if action in ('EXIT', 'START', 'QUIT'):
                self.controls.cancel()
                return False
            if action in ('L', 'R', 'TAB_PREV', 'TAB_NEXT'):
                return True  # tab switching is blocked while the page is open
            self.menu.handle(action)
            return True
        c = self.controller
        if (c.current_tab == 'SETTINGS' and c.current_param == PARAM and action == 'A'
                and not getattr(c, 'theme_subpage', False)
                and not getattr(c, 'debug_menu_active', False)
                and not getattr(c, 'ble_menu_active', False)):
            self.menu.open()
            c.console_edit = False
            if self.ui:
                self.ui.info_mode = False
            return True
        return False

    # --- native INFO panel text -------------------------------------------
    def info(self, language):
        i = 1 if str(language).upper() == 'RU' else 0
        preset = _core.active_preset(self.settings.data)
        shown = VALUES_RU.get(preset, preset) if i else preset
        prefix = '%s: %s. ' % (MESSAGES['preset'][i], shown.upper())  # visible without scrolling
        text = HELP['entry'][i] if not self.open else HELP.get(self._help_key(), HELP['None'])[i]
        return LABEL, prefix + text

    def _help_key(self):
        menu = self.menu
        key = menu.rows()[menu.index][0]
        if key == 'apply_preset':
            return menu.pending[1]
        if menu.page == 'root' and key in _core.CONTROLS:
            return 'stick' if key.endswith('stick') else 'click' if key in ('l3', 'r3') else 'button'
        if key == 'mode' and menu.page not in ('root', 'presets'):
            cfg = self.settings.data[menu.page.split('.')[0]]
            return 'Step' if cfg['effect'] in _core.STEP_EFFECTS else cfg['mode']
        if key in ('axis_x', 'axis_y'):
            return 'physical_axis'
        if key == 'effect':
            return self.settings.data[menu.page.split('.')[0]]['effect'] or 'None'
        return key if key in HELP else 'None'

    # --- drawing ---------------------------------------------------------------
    def draw(self, ui):
        """Subpage on the 1024x768 logical grid, same style as BLUETOOTH MIDI."""
        menu, lang = self.menu, _lang(ui)
        page = menu.page
        ui.draw_info_window(PARAM, top_y=115, bottom_y=292, left_x=55, right_x=970)
        pygame.draw.line(ui.screen, ui.VERY_DIM, (38, 300), (986, 300), 1)
        if menu.confirm:
            kind = menu.pending[0] if menu.pending is not None else 'reset'
            title = MESSAGES[kind + '_title'][lang]
            if kind == 'factory':
                title += ' ' + menu.pending[1].upper()
        elif page == 'root':
            title = LABEL
        elif page == 'presets':
            title = MESSAGES['presets_title'][lang]
        else:
            base = menu.LABELS[page.split('.')[0]]
            title = (LABELS_RU.get(base, base) if lang else base).upper()
            if page.endswith('.options'):
                title += ' / НАСТРОЙКИ' if lang else ' / OPTIONS'
        ui.text(title[:38], 55, 325, 4, ui.ACCENT)
        preset = _core.active_preset(self.settings.data)
        if page in ('root', 'presets') and not menu.confirm:
            shown = VALUES_RU.get(preset, preset) if lang else preset
            ui.text(('%s: %s' % (MESSAGES['preset'][lang], shown)).upper()[:26], 560, 335, 2, ui.DIM)
        pygame.draw.line(ui.screen, ui.VERY_DIM, (55, 381), (969, 381), 1)
        rows = menu.rows()
        visible = 7
        start = max(0, min(menu.index - 3, len(rows) - visible))
        for i in range(start, min(len(rows), start + visible)):
            key, label, value = rows[i]
            y = 392 + (i - start) * 42
            focused = i == menu.index
            disabled = False
            if not menu.confirm:
                if page == 'root':
                    disabled = key in _core.CONTROLS and not self.settings.data[key]['enabled']
                elif page == 'presets':
                    disabled = value == 'Unavailable' or (key == 'load_user' and self.settings.user_preset is None)
                else:
                    disabled = (not self.settings.data[page.split('.')[0]]['enabled']
                                and key not in ('back', 'enabled'))
            color = ui.ACCENT if focused else ui.DIM if disabled else ui.WHITE
            ui.text('>' if focused else ' ', 35, y, 3, ui.ACCENT)
            if lang:
                label = LABELS_RU.get(label, label)
                value = VALUES_RU.get(value, value)
            ui.text(str(label).upper()[:24], 65, y, 3, color)
            shown = str(value).upper()[:20]
            if focused and menu.edit:
                shown = '< ' + shown + ' >'
            ui.text(shown, 573, y, 3, color)
        if len(rows) > visible:
            ui.text('%d/%d' % (menu.index + 1, len(rows)), 894, 325, 2, ui.DIM)
        if self.settings.error:
            ui.text(MESSAGES['not_saved'][lang], 65, 676, 2, ui.ACCENT)

    def footer_items(self, ui):
        items = self._footer_items(ui)
        if _lang(ui):
            items = [(FOOTER_RU.get(text, text), color) for text, color in items]
        return items

    def _footer_items(self, ui):
        menu = self.menu
        if menu.edit:
            return [('LEFT/RIGHT CHANGE', ui.ACCENT), ('A/B DONE', ui.DIM)]
        if menu.confirm:
            return [('D-PAD NAV', ui.DIM), ('A CONFIRM', ui.ACCENT), ('B CANCEL', ui.DIM)]
        key = menu.rows()[menu.index][0]
        if key in menu.TOGGLES:
            return [('D-PAD NAV', ui.DIM), ('A TOGGLE', ui.ACCENT),
                    ('A+L/R QUICK', ui.DIM), ('B BACK', ui.DIM)]
        if key in menu.VALUES:
            return [('D-PAD NAV', ui.DIM), ('A EDIT', ui.ACCENT),
                    ('A+L/R QUICK', ui.DIM), ('B BACK', ui.DIM)]
        return [('D-PAD NAV', ui.DIM), ('A OPEN', ui.ACCENT), ('B BACK', ui.DIM)]


def _attach():
    global _attached
    if _attached:
        return True
    names = ('engine.control', 'engine.input', 'engine.autokey', 'ui.renderer')
    modules = [sys.modules.get(n) for n in names]
    if any(m is None for m in modules):
        return False
    control, inputs, autokey, renderer = modules
    C, I, A, U = control.ControlManager, inputs.InputManager, autokey.AutoKeyAdapter, renderer.UIEngine
    needed = (hasattr(C, 'SETTINGS_PARAMS') and hasattr(C, 'handle') and hasattr(A, 'events')
              and all(hasattr(U, x) for x in ('draw_settings_page', '_save_settings', '_gb_draw_footer',
                                              'draw_info_window', 'draw_bar_items', 'SETTINGS_PATH'))
              and hasattr(renderer, 'get_context_info') and hasattr(I, 'poll') and hasattr(I, 'close'))
    if not needed:
        _log('unsupported BETA 2.0 engine, original controls retained')
        return False
    old_init, old_handle, old_ui = C.__init__, C.handle, U.__init__
    old_draw, old_save, old_footer = U.draw_settings_page, U._save_settings, U._gb_draw_footer
    old_poll, old_close, old_events = I.poll, I.close, A.events

    def ensure(ui=None):
        gb_settings_rows.register(
            C, ui, PARAM, LABEL,
            lambda: _core.active_preset(_runtime.settings.data).upper() if _runtime else '>')

    def init(self, *args, **kw):
        global _runtime
        old_init(self, *args, **kw)
        _runtime = Runtime(self, U.SETTINGS_PATH)

    def ui_init(self, *args, **kw):
        old_ui(self, *args, **kw)
        if _runtime:
            _runtime.ui = self

    def handle(self, action, value=None):
        if _runtime and _runtime.controller is self and _runtime.handle(action):
            return
        result = old_handle(self, action, value)
        if _runtime and _runtime.controller is self and not _runtime.performance():
            _runtime.controls.release_transient()  # Toggle effects stay across tabs
        return result

    def events(self, *args, **kw):
        result = old_events(self, *args, **kw)
        return _runtime.filter_events(result) if _runtime else result

    def draw(self, controls):
        ensure(self)
        if _runtime and _runtime.open and controls.current_tab != 'SETTINGS':
            _runtime.menu.page = None  # another layer switched the tab
            _runtime.menu.edit = False
        if _runtime and _runtime.open:
            _runtime.draw(self)
            return
        return old_draw(self, controls)

    def footer(self, controls, audio_worker):
        if _runtime and _runtime.open and controls.current_tab == 'SETTINGS':
            pygame.draw.line(self.screen, self.VERY_DIM, (38, 702), (986, 702), 1)
            self.draw_bar_items(_runtime.footer_items(self), left=54, right=795)
            return
        return old_footer(self, controls, audio_worker)

    def save(self):
        # Native settings changes must not erase our nested configuration.
        preserved = None
        if _runtime:
            try:
                preserved = _runtime.settings._read()
            except (OSError, ValueError, TypeError):
                pass
        result = old_save(self)
        if _runtime:
            _runtime.settings.save(preserved)
        return result

    def poll(self, *args, **kw):
        if _runtime:
            _runtime.input = self
        result = old_poll(self, *args, **kw)
        if _runtime:
            _runtime.tick(self)
            if any(action in ('EXIT', 'QUIT') for action, value in result):
                _runtime.controls.cancel()  # unwind before main saves its sound state
            if _runtime.open:
                # SELECT is intercepted by main before ControlManager.
                result = [(a, v) for a, v in result if a != 'SELECT']
        return result

    def close(self):
        if _runtime:
            _runtime.controls.cancel()
        return old_close(self)

    C.__init__, C.handle = init, handle
    U.__init__, U.draw_settings_page, U._save_settings, U._gb_draw_footer = ui_init, draw, save, footer
    gb_settings_rows.register_info(U, renderer, PARAM, lambda language: _runtime.info(language))
    I.poll, I.close, A.events = poll, close, events
    _attached = True
    _log('attached to native Settings / ParameterBus')
    return True


def install():
    global _installed
    if _installed or os.environ.get('GRAINBERNIK_ADVANCED', '1') == '0':
        return
    old = pygame.init

    def init(*args, **kw):
        _attach()
        return old(*args, **kw)

    pygame.init = init
    atexit.register(lambda: _runtime.controls.cancel() if _runtime else None)
    _installed = True
    _log('installed; waiting for native engine initialization')
