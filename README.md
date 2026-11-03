# GrainBernik

[English](README.md) | [Русский — полная инструкция](README_RU.md)

**GrainBernik** is an unofficial fork of [ETRNLIAM/GrainBrick](https://github.com/ETRNLIAM/GrainBrick) for the **Anbernic RG40XX H** (640×480) running KNULLI.

GrainBrick beta 1.0.1 adds adaptive display resolution, controls and USB audio. GrainBernik keeps the RG40XX H button and Advanced Settings adapters. It leaves the new native display and USB audio handling in control by default; the older scaling and USB recording adapters remain opt-in.

The patch does not modify or redistribute the closed GrainBrick application: you still need the official release ZIP from the original author.

> Status: beta. The earlier GrainBrick beta 1.0 adaptation was tested on RG40XX H. The author has confirmed beta 1.0.1 on RG40XX V, but not RG40XX H; this adaptation still needs device verification.

**Download:** [GrainBernik v0.1.1-beta.1](https://github.com/AlekseyMalykh/GrainBernik/releases/tag/v0.1.1-beta.1).
Choose the **patch ZIP** for a fresh installation over official GrainBrick
beta 1.0.1, or the **update ZIP** for an existing GrainBernik installation.
The original closed application is not bundled. See [release notes](docs/releases/v0.1.1-beta.1.md).

**Advanced Settings — working on RG40XX H.** The in-app **Settings → Advanced Settings** menu adds independent Left Stick, Right Stick, L2 and R2 assignments. All four start **OFF**. The owner confirmed successful operation of the initial version on RG40XX H with KNULLI on **2026-11-03**. Beta.1 passed **30 control/configuration checks and 18 integration checks against the official ARM64 application and DSP**; the beta.2 language fix has not been retested. The detailed checklist below remains useful for checking every assignment and longer sessions; the device confirmation is not an exhaustive compatibility report.

**Latest update:** **v0.1.1-beta.1** integrates the official GrainBrick 1.0.1 update while keeping the prior English menu labels and INFO LANGUAGE-controlled hints. The updated fork has not yet been retested on the device.

## Install on RG40XX H

1. Download the official `grainbrick.beta.1.0.1.zip` from the [original releases](https://github.com/ETRNLIAM/GrainBrick/releases). Copy `grainbrick beta 1.0.1/` and `GrainBrick beta 1.0.1.sh` to `/userdata/roms/ports/` (the `roms/ports` folder on SHARE when the card is in a PC).
2. Copy the files from [`rg40xx-h-patch/grainbrick-beta/`](rg40xx-h-patch/grainbrick-beta/) into `/userdata/roms/ports/grainbrick beta 1.0.1/`, replacing `gb_launch.py`:
   - `gb_display_fit.py` — optional screen adapter for beta 1.0; disabled by default on 1.0.1;
   - `gb_buttons.py` — the button layout adapter;
   - `gb_audio.py` — legacy USB recording adapter for beta 1.0; disabled by default on 1.0.1;
   - `gb_advanced.py` and `gb_advanced_controls.py` — the in-app Advanced Settings and live control adapter (copy **both** files);
   - `gb_launch.py` — the original launcher plus a few lines that load the adapters.
3. Copy [`rg40xx-h-patch/GrainBernik Buttons Setup.sh`](rg40xx-h-patch/) (and optionally `GrainBernik Audio Check.sh`) into `/userdata/roms/ports/`.
4. Launch GrainBrick from PORTS. On the first launch a short button setup screen appears: press each button it asks for (A, B, X, Y, L1, R1, L2, R2, SELECT, START, MENU, D-pad, then optionally L3/R3 for TAB−/TAB+). Optional steps are skipped automatically after a few seconds.

**Updating an existing GrainBernik installation:** install the official beta 1.0.1 into its new `grainbrick beta 1.0.1/` folder, then copy the update ZIP contents there. Keep your existing `gb_buttons.json`, `settings.json`, `sound_state.json`, samples, projects and recordings. Copy user data only if needed; do not remove the old app folder until the new version has been checked on the device.

### Buttons

`gb_buttons.py` records the RG40XX H button layout in `gb_buttons.json` and translates button events for GrainBrick. The new upstream controls are used where available; the adapter preserves the established button labels and hints.

To redo the setup, run **GrainBernik Buttons Setup** from PORTS (or delete `gb_buttons.json`). Set `GRAINBRICK_BUTTONS=0` to turn the adapter off.

### Advanced Settings

Open **SETTINGS**, select **ADVANCED SETTINGS**, then press **A** or **D-pad Right**. Four submenus configure **Left Stick**, **Right Stick**, **L2 Button** and **R2 Button** independently. D-pad Up/Down selects a row; Left/Right or A changes its value; B goes back. Disabled controls stay editable and keep their assignments. Stick Options scrolls when needed; Reset to Defaults requires confirmation and resets only these extra controls.

**START** plays/stops without closing the menu. **L1/R1** switches the main tabs and closes the submenu; edited assignments are already saved and remain available when you return. Navigation/transport hints and contextual explanations follow the native **INFO LANGUAGE** setting (**EN/RU**) immediately. Menu labels, option names, confirmation titles and save-error messages stay in English; effect and parameter names retain the app's English naming.

As in the native menus, the selected setting's title and explanation appear
**above the control list**. Button and transport hints remain at the bottom.

- **Sticks:** separate X/Y parameter assignments, including None; 12% default deadzone; sensitivity, X/Y inversion, Spring/Latch and time-based smoothing. The list is filtered using the running engine's real parameter bounds. Default physical axis indices are left 0/1 and right 2/3; Stick Options allows correcting them for a different controller layout. Calibrated analog-trigger axes are reserved.
- **L2/R2:** independently choose **Hold** or **Toggle**, and **Freeze**, **Reverse**, **Delay Throw**, **Reverb Wash**, **Pitch Drop**, **Bypass**, **ORBIX** or **None**. These are reversible presets of existing engine parameters. Freeze uses native **Motion Hold** fragments, Reverse uses native Motion Reverse, and Bypass bypasses the delay/reverb/shimmer, tape, compressor and EQ processing while preserving sample/grain playback. ORBIX enables the native generator and restores its previous enable state on deactivation; it does not automatically change transport playback.
- **Settings:** automatically saved under `grainbernik_advanced` in the existing `settings.json`; native app settings are preserved. All assignments start OFF. Turning a control OFF retains its selected parameters. Read/write failures are shown in the advanced menu.
- **Scope:** assignments operate on the GRAIN, FX, TAPE and VISUAL tabs. Browsing samples, Settings, Save, help/button rebinding, loss of focus, controller removal and exit release temporary effects. Spring returns to the gesture's initial value; Latch retains the last value at center until the control is disabled or a non-performance screen is entered. Returning from a menu requires a fresh button press or centered stick.
- **Available XY parameters in beta 1.0:** Grain Position/Size/Density/Pitch/Spray; Delay Time/Feedback/Mix/Lowpass; Reverb Mix/Size/Decay; Shimmer Amount/Pitch; Roam Speed; Tape Saturation/Wow/Flutter. Grain and motion parameters require their respective native processing modes to be active.
- **ORBIX XY:** Gravity, Rotation, Bounce, Volume, Attack, Release, Reverb, Balls, Root, Scale, Instrument, Octave and Shape. Counts and musical selections are published as integers. XY changes do not silently enable ORBIX: turn it on natively or assign ORBIX to L2/R2, then use START for playback. All **31** XY choices are filtered against the running engine.
- **Limits:** the current public ParameterBus does not expose Filter Cutoff/Resonance, Tape Speed or Pan. No direct Stutter, Tape Stop or Glitch API was verified, so these are **not offered**. Delay Throw/Reverb Wash are parameter presets, not a new send/return routing system. Original closed application/DSP files remain unmodified.

Detailed behavior, test commands and the on-device checklist: [Advanced Settings](docs/ADVANCED_SETTINGS.md). Set `GRAINBERNIK_ADVANCED=0` to disable this adapter.

### Control presets

Open **Advanced Settings → Presets**. Five built-in layouts configure all four
controls; **Save Current** and **Load User** manage one independent User slot.
Applying/loading a layout or replacing User requires confirmation, initially
focused on Cancel. No preset is applied automatically on upgrade.

| Preset | Left stick X / Y | Right stick X / Y | L2 / R2 | Sensitivity / smoothing |
|---|---|---|---|---|
| Granular | Grain Position / Size | Grain Pitch / Density | Freeze / Reverse | 70% / 60 ms |
| Ambient | Grain Position / Spray | Reverb Mix / Shimmer Amount | Freeze / Reverb Wash | 50% / 180 ms |
| Echo | Delay Time / Feedback | Delay Mix / Reverb Mix | Delay Throw / Reverb Wash | 50% / 100 ms |
| Tape | Tape Saturation / Wow | Grain Pitch / Tape Flutter | Pitch Drop / Bypass | 40% / 140 ms |
| ORBIX Play | ORBIX Rotation / Gravity | ORBIX Bounce / Reverb | ORBIX Toggle / Reverb Wash | 50% / 120 ms |

Factory layouts enable all four controls, use Spring sticks and Hold buttons
(except ORBIX Toggle), and preserve current axis indices, deadzone and inversion.
They change control assignments, not the sound parameters or transport. Native
grain/tape processing still needs enabling when appropriate.

On the first factory application, an empty User slot automatically saves your
previous setup. Later factory choices never overwrite that slot. Save Current
explicitly replaces it after confirmation; Load User restores all four controls
and their options after restart as well. Reset to Defaults keeps the saved User
slot. A failed preset save leaves both the active setup and User unchanged.

### USB audio

- **Output** works out of the box: connect a class-compliant USB audio device *before* starting GrainBrick and choose it in the app's OUTPUT setting.
- **Recording**: GrainBrick records "USB AUDIO" from a fixed device (`hw:1,0`, exactly 48 kHz / 16 bit / stereo), which on the RG40XX H is usually not the USB card and rejects devices with other formats. `gb_audio.py` redirects that recording to the first USB card that can record, through ALSA `plughw`, so sample rate, bit depth and channel count are converted automatically. Choose **USB AUDIO** as the input source on the recording page.
- The RG40XX H has no built-in microphone, so the BUILT-IN MIC source does not work.
- Tested with a **Zoom H1n**: micro-USB to USB-C data cable into the OTG port, on the recorder choose *Audio Interface → PC/Mac*. Batteries in the H1n make the connection more reliable.
- An iPhone cannot be used as a USB sound card on Linux.
- If a device doesn't show up, run **GrainBernik Audio Check** from PORTS with it connected; it writes `grainbrick beta 1.0.1/audio_check.txt` with what the system sees.
- Optional: `GRAINBRICK_USB_IN=plughw:CARD=<id>,DEV=0` forces the capture device, `GRAINBRICK_AUDIO=0` turns the adapter off.

Optional settings (environment variables, can be added to `GrainBrick beta 1.0.1.sh` before the `python3` line):

| Variable | Values | Meaning |
|---|---|---|
| `GRAINBRICK_SCREEN` | e.g. `640x480` | Force the real screen size (default: auto-detect) |
| `GRAINBRICK_SCALE` | `smooth` / `fast` | Scaling quality. `smooth` is the default and switches to `fast` automatically if the CPU is too slow |
| `GRAINBERNIK_FIT` | `1` | Enable the legacy display adapter on GrainBrick 1.0.1 |
| `GRAINBERNIK_LEGACY_AUDIO` | `1` | Enable the legacy USB recording adapter on GrainBrick 1.0.1 |
| `GRAINBERNIK_ADVANCED` | `0` | Disable the Advanced Settings/control adapter |

On GrainBrick beta 1.0.1, check `grainbrick beta 1.0.1/gb_launch.log` for adapter status. The upstream native display handler is used by default.

## Установка на RG40XX H (кратко)

Для установки скачайте `grainbrick.beta.1.0.1.zip`, затем скопируйте адаптеры из `rg40xx-h-patch/grainbrick-beta/` в `roms/ports/grainbrick beta 1.0.1/`. На этой версии GrainBernik оставляет родные адаптивный экран и USB-аудио активными; старые адаптеры экрана и USB-записи включаются только переменными окружения из таблицы выше. Первая настройка кнопок запускается автоматически.

### Расширенные настройки

Внутри программы: **SETTINGS → ADVANCED SETTINGS**. Это новый пункт существующих настроек, а не отдельный порт. В нём четыре независимых подменю: **Left Stick**, **Right Stick**, **L2 Button**, **R2 Button**. Все четыре назначения изначально выключены. Крестовина вверх/вниз выбирает строку, влево/вправо или A меняют значение, B возвращает назад. Выключенные элементы приглушены, но доступны для настройки. Сброс этих настроек требует подтверждения.

Стикам назначаются отдельные параметры X/Y или None. Есть мёртвая зона (по умолчанию 12%), чувствительность, инверсия осей, сглаживание и режимы Spring/Latch. Spring возвращает значение к началу жеста, Latch оставляет последнее значение после отпускания стика. В Stick Options также можно поменять номера физических осей, если стандартные 0/1 и 2/3 не подходят устройству.

L2/R2 поддерживают Hold/Toggle и назначения **Freeze, Reverse, Delay Throw, Reverb Wash, Pitch Drop, Bypass, None**. Это управление существующими параметрами: Freeze — штатное удержание фрагментов Motion Hold, Reverse — Motion Reverse; Bypass отключает эффекты, сохраняя воспроизведение. Отдельные Stutter/Tape Stop/Glitch, Filter Cutoff/Resonance, Tape Speed и Pan не добавлены: рабочего доступа к ним в текущей шине не найдено. Список XY включает только реально доступные параметры гранулятора, delay, reverb, shimmer и tape, а также Roam Speed.

**Теперь доступен ORBIX:** для X/Y добавлены Gravity, Rotation, Bounce, Volume, Attack, Release, Reverb, Balls, Root, Scale, Instrument, Octave и Shape. Дискретные параметры меняются целыми значениями. На L2/R2 можно назначить **ORBIX** в Hold/Toggle: кнопка включает генератор и затем возвращает его прежнее состояние. START отдельно управляет воспроизведением.

**Исправлено управление в подменю:** START запускает/останавливает воспроизведение, L1/R1 переключают основные вкладки с сохранением назначений. Подсказки выбранного пункта и кнопок следуют настройке **INFO LANGUAGE: EN/RU**. Названия меню, заголовки подтверждений и ошибки сохранения остаются на английском. [Полная русская инструкция](README_RU.md).

**Пресеты управления:** в **Advanced Settings → Presets** доступны Granular,
Ambient, Echo, Tape и ORBIX Play, а также один пользовательский слот с командами
«Сохранить текущую» и «Загрузить свою». Замена требует подтверждения.
Первая готовая раскладка сохраняет предыдущие настройки в пустой User;
последующие раскладки его не перезаписывают. Калибровка осей сохраняется,
сброс к стандартным не удаляет User. [Таблица раскладок и подробности](README_RU.md#пресеты-управления).

Настройки автоматически сохраняются в существующий `settings.json`, в раздел `grainbernik_advanced`. Выключение не стирает назначения. Управление действует на вкладках GRAIN/FX/TAPE/VISUAL. При входе в браузер, настройки, сохранение или справку, при потере фокуса, отключении контроллера и выходе временные эффекты снимаются, включая Toggle/Latch. После возвращения нужна новая кнопка или возврат стика в центр.

**Работа первой версии подтверждена владельцем на RG40XX H с KNULLI 3 ноября 2026 года**. Beta.1 прошла **48 автопроверок**: 30 логических и 18 с ARM64-приложением и оригинальным DSP. Локализационная правка beta.2 пока не проходила повторные автотесты и ожидает проверки на консоли. [Подробный сценарий](docs/ADVANCED_SETTINGS.md).

Для обновления уже установленного GrainBernik достаточно скопировать **`gb_advanced.py`, `gb_advanced_controls.py` и обновлённый `gb_launch.py`**. Существующие адаптеры звука/кнопок/экрана, USB-скрипты, настройки, сэмплы, проекты и записи сохраняйте. Перед заменой сделайте резервную копию загрузчика и настроек.

---

*Original README of GrainBrick below.*

# GrainBrick

A free granular ambient sound instrument for TrimUI Brick.

GrainBrick turns audio samples into evolving, organic textures with granular processing, tape-style sound shaping, effects and the ORBIX generative note engine.

It is designed for hands-on ambient exploration and sound design - not a tracker, sequencer or traditional looper.

## Official GrainBrick beta 1.0.1

This update adds adaptive resolution and controls, improved Anbernic compatibility and automatic USB audio input detection. RG40XX V is listed as tested by the author; RG40XX H is not.

## Features

- Granular sample processing and evolving ambient textures
- ORBIX generative note engine
- Reverb, delay, shimmer and other sound-shaping effects
- Tape-style processing
- Recording and trimming audio, including the Brick's internal microphone
- USB audio input/output support on compatible devices
- Project saving and contextual parameter help

## Download

Open the [original repository's Releases section](https://github.com/ETRNLIAM/GrainBrick/releases) and download:

GrainBrick_beta_1.0_TrimUI_Brick_KNULLI.zip

Do not download GitHub's automatically generated “Source code” ZIP - that is not the application.

## Compatibility

- Tested: original TrimUI Brick with KNULLI
- Requires a compatible AArch64 KNULLI installation providing Python 3.12, Pygame and NumPy
- Other handhelds, operating systems and TrimUI Brick Pro have not been confirmed compatible

## Installation

1. Download the release ZIP and extract its contents.
2. Copy both `grainbrick beta 1.0.1/` and `GrainBrick beta 1.0.1.sh` to `/userdata/roms/ports/`.
3. Refresh your PORTS list in KNULLI.
4. Launch GrainBrick beta 1.0.1.

When upgrading, preserve your samples, projects, recordings and settings. Keep the old folder until the updated release has been checked on your device.

## Feedback

This is a beta release. Please use the repository's Issues section to report reproducible bugs and hardware compatibility findings, including your OS version and device model.

## Licensing

GrainBrick is free to download, but its original application source code is currently closed. An open public beta does not mean that the GrainBrick source code is open source.

The distribution includes notices and applicable source materials for its bundled third-party components, including LGPL-licensed SoundTouch. See THIRD_PARTY_NOTICES.md, THIRD_PARTY_LICENSES/ and THIRD_PARTY_SOURCES/ inside the downloadable release.
