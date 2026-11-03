# Advanced Settings / Расширенные настройки

This feature extends the official GrainBrick beta 1.0 **in process**, from the
existing Settings tab. It requires both `gb_advanced.py` and
`gb_advanced_controls.py` alongside the updated `gb_launch.py`.

**Device status (2026-11-03):** the owner confirmed successful operation on
RG40XX H with KNULLI after the three-file update was installed on the console's
card. Beta.1 passed **48 tests** (30 pure tests and 18 tests against the official
ARM64 application/DSP). The beta.2 language-scope fix has not been retested yet.
The checklist below covers additional per-assignment and extended testing; not
every item has been individually confirmed by the owner.

## Menu and navigation

```text
SETTINGS
  INFO LANGUAGE
  SAVE PARAMS ON EXIT
  AUDIO OUTPUT LIVE
  BUTTON MAPPING
  RESET SOUND PARAMS
  ADVANCED SETTINGS
    LEFT STICK
      Enabled / X Effect / Y Effect / Stick Options / Back
    RIGHT STICK
      Enabled / X Effect / Y Effect / Stick Options / Back
    L2 BUTTON
      Enabled / Effect / Mode / Back
    R2 BUTTON
      Enabled / Effect / Mode / Back
    Presets
      Granular / Ambient / Echo / Tape / ORBIX Play
      Load User / Save Current / Back
    Reset to Defaults → Cancel / Restore Defaults
    Back
```

Up/Down moves selection, Left/Right changes values, A opens/changes, B returns
one level. START toggles native playback without closing the menu. L1/R1 and
the calibrated TAB−/TAB+ controls leave the submenu and switch the native main
tabs; assignments remain saved. Stick Options has scrolling
and a row counter. The original pixel font, colors and 1024×768 virtual surface
are retained and scaled by the existing adapter to 640×480. No mouse is needed.
Disabled controls remain editable; enabling one does not enable any other.
The Reset Sound Params entry remains the original app action; the new Reset
to Defaults affects only the four advanced assignments and needs confirmation.

Contextual explanations for the selected setting and navigation/transport hints
follow native INFO LANGUAGE (EN/RU). Menu labels, option names, confirmation
titles and save-error messages stay in English. Changes apply on the next render;
no restart is needed. Parameter/effect names retain the existing app naming. As
in native menus, the selected setting title and its two-line context help sit
above the control list. Navigation and transport hints remain at the bottom.

## Configuration

The original `settings.json` contains an additional `grainbernik_advanced`
object with `version: 1` and `left_stick`, `right_stick`, `l2`, `r2` objects.
The default for **every** `enabled` is false. Native settings saves merge this
object back into the document; advanced saves preserve existing native keys.
Writes use an adjacent temporary file, flush/fsync and atomic replacement.
No writes occur per audio frame or stick motion; only configuration changes
save the file. Failed saves remain visible in the menu.

Each stick stores `enabled`, `x`, `y`, `deadzone` (0–50%, default 12),
`sensitivity` (10–200%, default 100), `invert_x`, `invert_y`, `mode`
(Spring/Latch, default Spring), `smoothing` (0–500 ms, default 60), and
`axis_x`, `axis_y` (default left 0/1, right 2/3). Every axis can be None.
Unavailable parameters are not offered, but a previously saved unavailable
assignment is displayed as Unavailable instead of silently changing its sound.
Calibrated analog-trigger axes cannot also modulate XY parameters. Correct
physical stick indices in Stick Options if the console reports another order.

Each trigger stores `enabled`, `effect` (or null/None) and `mode`
(Hold/Toggle, default Hold). Disabling keeps the assignment. Active Hold,
Toggle and Latch states are temporary and are not resumed at startup.

## Control presets and User slot

The Presets submenu offers Granular, Ambient, Echo, Tape and ORBIX Play.
The [README table](../README.md#control-presets) lists exact assignments,
sensitivity and smoothing. All factory layouts use Spring, enable all four
controls, and use Hold except the ORBIX Toggle button. Current physical axis
indices, deadzone and inversion are preserved. Native audio parameters and
transport are not reconfigured; no factory layout activates automatically.

Apply, Load User and Save Current open a confirmation focused on Cancel. The
confirmation names the factory layout. Unsupported factory mappings cannot be
applied. Cancel or leaving via L1/R1 leaves assignments and the User slot intact;
START remains available. Preset help and confirmation are translated EN/RU.

`grainbernik_advanced.user_preset` stores either null or a flat, validated
snapshot of all four controls, including their options and physical axes.
Existing version-1 configurations without this key keep their active layout
and start with an empty slot. A first factory application automatically archives
that layout into an empty User slot; subsequent factory applications preserve
an occupied slot. Explicit Save Current replaces it after confirmation. Load
User restores it, including after process restart. Reset to Defaults affects
active controls only and preserves User. Snapshots are independent copies and
do not include nested preset metadata or active Hold/Toggle states.

Preset save uses the same atomic configuration write. On failure, both in-memory
active assignments and User are rolled back, and the previous on-disk file
remains intact. Native settings changes merge the slot back into settings.json.
Switching layouts cancels any old transient modulation before reassigning input.

## XY behavior

Both axes use an axial deadzone, remapped continuously outside that deadzone.
The value at the beginning of a gesture is the center reference; full stick
deflection moves by half the engine's parameter range at 100% sensitivity.
Values are clamped to bounds read from the actual Parameter objects. This is
relative expression around the current sound, not a jump to a fixed midpoint.
Y inversion is optional; by default the raw SDL sign is retained.

Spring smooths back to the starting value. Latch holds the last applied value
when the stick centers; a new deflection starts relative to that value.
Smoothing is a time-based one-pole response, not a fixed increment per frame.
The original engine's DSP smoothing remains active. XY control does not
automatically turn granular/tape processing on: activate the corresponding
native mode when using its parameters.

ORBIX offers seven continuous axes (Gravity, Rotation, Bounce, Volume, Attack,
Release, Reverb) and six discrete axes (Balls, Root, Scale, Instrument, Octave,
Shape). Discrete targets are rounded to valid integers **before** publishing
to ParameterBus; unchanged integer selections do not generate repeated writes.
Bounds still come from the native engine. XY assignments do not turn ORBIX on
or start transport. Enable it using the native control or the ORBIX L2/R2
assignment and use START for playback.

If several controls target the same parameter, the deterministic priority is
left stick X/Y, right stick X/Y, L2, R2. Releasing one reveals the remaining
control's value; releasing the last restores the original value. Native edits
made while a parameter is overridden become the new underlying value. These
rules avoid one trigger's release undoing the other trigger's still-active FX.

## Real beta 1.0 assignments

XY choices are None plus the following **31** parameters, filtered against the
running ParameterBus:

| Group | Assignments |
|---|---|
| Grain | Position, Size, Density, Pitch, Spray |
| Delay | Time, Feedback, Mix, Lowpass |
| Reverb | Mix, Size, Decay |
| Shimmer | Amount (mix), Pitch (shift) |
| Tape | Saturation, Wow, Flutter |
| Roam | Speed |
| ORBIX | Gravity, Rotation, Bounce, Volume, Attack, Release, Reverb, Balls, Root, Scale, Instrument, Octave, Shape |

| Button assignment | Existing engine parameters / behavior |
|---|---|
| Freeze | Enables grain and motion; sets `motion.hold` to 1. Native frozen **fragment** texture, not spectral freezing. |
| Reverse | Enables motion; sets `motion.reverse` to 1. Native reversal of motion inside the audio flow, not file reversal. |
| Delay Throw | Sets delay mix to 0.65 and feedback to 0.6; restores both on release/deactivation. |
| Reverb Wash | Sets reverb mix to 0.85, size to 0.95, decay to 12 s; restores these on release/deactivation. |
| Pitch Drop | Enables grain processing and sets grain pitch to −12 semitones; restores both. |
| Bypass | Delay/reverb/shimmer mix 0, tape/comp disabled, six EQ gains 0; restores all on release/deactivation. |
| ORBIX | Sets `orbix.enabled` to 1; restores its previous value on release/deactivation, including when it was already enabled. Does not change transport or the other ORBIX settings. |
| None | No extra input capture or sound changes. |

All button assignments offer Hold and Toggle. Values are clamped using the
running engine's bounds. These are parameter macros, not newly implemented
audio algorithms. Delay Throw is not a separate input-send effect: the public
API does not expose an independent send/return route. No promises are made
about audible tails when mix is restored to zero.

**Not exposed by the inspected beta 1.0 ParameterBus:** Filter Cutoff,
Filter Resonance, Tape Speed and Pan. Existing text references to a filter do
not constitute a working ParameterBus API. No direct Stutter, Tape Stop or
Glitch API was verified; these are omitted rather than simulated.

## Input ownership and safety

Extra controls operate in GRAIN, FX, TAPE and VISUAL. They release on entering
Sample/browser, Settings, Save or help, rebinding buttons, losing focus,
controller removal or app exit. This includes latched effects. The original
sample browser/recording/settings controls remain in charge on those pages.
Button-down/up pairs owned by advanced effects are consumed together. A held
button cannot immediately re-engage after a menu; release and press again.
Sticks must pass through center after suspension to prevent a sudden jump.
Disabled assignments and None do not consume their input events.

`gb_buttons.py` still calibrates/translates physical buttons before this
adapter receives them. L2/R2 refer to the physical calibrated triggers, not
arbitrary actions reassigned in the original Button Mapping screen. That
screen always receives its input normally while capturing a new binding.

No original `.so`, DSP library or original application source is edited or
redistributed. The launcher attaches wrappers to the public `ControlManager`,
`InputManager`, `UIEngine` and `ParameterBus` of the installed official release.
Use `GRAINBERNIK_ADVANCED=0` to disable the adapter.

## Automated checks

Pure configuration, menu and control checks, on any Python 3.12:

```sh
python -m unittest discover -s tests -p test_advanced_controls.py -v
```

Optional tests against an official **ARM64** release on ARM64 Python 3.12
(or under qemu-aarch64 with its ARM64 dependencies):

```sh
GRAINBRICK_OFFICIAL_DIR=/path/to/official/grainbrick-beta \
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy \
GRAINBERNIK_TEST_OUTPUT=test-output \
python3 -m unittest discover -s tests -v
```

The native suite checks the real bootstrap hook, unchanged existing settings
entries, physical-button/D-pad navigation through native `InputManager.poll`,
actual `UIEngine` rendering, real ParameterBus limits, XY, Hold/Toggle,
native/advanced configuration merging, input capture/focus cleanup and
rendering each macro through the original `GranularEngine`/`DSPChain`.
It also verifies ORBIX generating audio from a silent input sample, integer
musical selections, START from every advanced page, shoulder-button tab changes
with saved assignments and both help languages with 640×480 render captures.
Preset checks cover legacy-config migration, all five factory layouts, preserved
calibration, first-use archive, User save/load/overwrite, cancellation, unsupported
mappings, save-failure rollback and the native app's settings-save path.
Without an official module, native tests are explicitly skipped, not counted
as device verification. The module itself is never copied into this repository.

## Проверка на RG40XX H

Владелец подтвердил успешную работу функции на RG40XX H с KNULLI
**3 ноября 2026 года**. Автотесты дополнительно используют настоящий
ARM64-модуль и оригинальный DSP. Ниже — сценарии для повторной проверки
отдельных назначений, обновлений и длительной работы; прохождение каждого
пункта отдельно пока не зафиксировано.

1. Скопировать все шесть `.py` адаптера с обновлённым `gb_launch.py`.
   Для уже установленного GrainBernik достаточно двух новых файлов
   `gb_advanced.py`, `gb_advanced_controls.py` и обновлённого `gb_launch.py`;
   остальные адаптеры, настройки и пользовательские данные сохраняются.
   Открыть SETTINGS → ADVANCED SETTINGS. Проверить читаемость и крестовину/A/B,
   доступность всех старых настроек, прокрутку Stick Options и отмену сброса.
2. Убедиться, что при первом запуске все четыре назначения OFF и штатное
   управление работает как раньше. Настроить каждый отдельно, выключить
   один — остальные должны остаться без изменений.
3. Включить левый стик с Position/Size, правый с Delay Mix/Reverb Mix.
   Проверить номера и знаки осей, None на каждой оси, центр, мёртвую зону,
   чувствительность, инверсию, Spring/Latch и сглаживание на слух.
4. Для L2/R2 проверить каждый эффект, Hold и Toggle, оба одновременно,
   общий параметр двух кнопок и отпускание в разном порядке. Для Freeze
   ожидать Motion Hold фрагментов, для Reverse — штатный Motion Reverse.
5. При активном эффекте открыть Settings, Sample, Save, справку. Ничего не
   должно зависать; после возврата удерживаемые органы не должны сами
   повторно включать эффект. Проверить выход и повторный запуск программы.
6. Проверить сохранение всех настроек после перезапуска, сохранность
   исходных назначений после OFF/ON и старых настроек приложения после
   изменения любого нативного пункта.
7. Проверить запись, выбор/предпрослушивание сэмплов, сохранение проектов,
   USB-аудио и длительную работу четырёх назначений одновременно. Сравнить
   нагрузку и проверить отсутствие новых щелчков/пропусков звука.
