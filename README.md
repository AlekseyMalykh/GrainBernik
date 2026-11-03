# GrainBernik

[English](README.md) | [Русский — полная инструкция](README_RU.md)

**GrainBernik** is an unofficial fork of [ETRNLIAM/GrainBrick](https://github.com/ETRNLIAM/GrainBrick) for the **Anbernic RG40XX H** (640×480) running KNULLI.

GrainBrick draws its interface for the TrimUI Brick screen (1024×768). On a 640×480 screen you only see the top-left part of it. This fork adds a small launcher patch: the app keeps drawing at 1024×768 off-screen, and every frame is scaled down to the real screen. Both screens are 4:3, so the picture fills the whole display.

The patch does not modify or redistribute the closed GrainBrick application: you still need the official release ZIP from the original author.

> Status: beta. Tested on RG40XX H with KNULLI: screen scaling, buttons, USB audio output and USB recording (Zoom H1n as audio interface).

**New: Advanced Settings — working on RG40XX H.** The in-app **Settings → Advanced Settings** menu adds independent Left Stick, Right Stick, L2 and R2 assignments. All four start **OFF**. The owner confirmed successful operation of the initial version on RG40XX H with KNULLI on **2026-11-03**. Automated checks now cover **21 control/configuration tests and 15 integration tests against the official ARM64 application and DSP**. The detailed checklist below remains useful for checking every assignment and longer sessions; the device confirmation is not an exhaustive compatibility report.

**Latest update:** ORBIX assignments (13 XY parameters and a Hold/Toggle button), START playback control and L1/R1 tab switching from every advanced submenu, and contextual/navigation help following **INFO LANGUAGE → EN/RU**. These additions pass automated checks and await a new on-device check.

## Install on RG40XX H

1. Install the official release as described below (copy `grainbrick-beta/` and `GrainBrick beta 1.0.sh` to `/userdata/roms/ports/`). With the card in a PC, this is the `roms/ports` folder on the SHARE partition.
2. Copy the files from [`rg40xx-h-patch/grainbrick-beta/`](rg40xx-h-patch/grainbrick-beta/) into `/userdata/roms/ports/grainbrick-beta/`, replacing `gb_launch.py`:
   - `gb_display_fit.py` — the screen adapter;
   - `gb_buttons.py` — the button layout adapter;
   - `gb_audio.py` — the USB recording adapter;
   - `gb_advanced.py` and `gb_advanced_controls.py` — the in-app Advanced Settings and live control adapter (copy **both** files);
   - `gb_launch.py` — the original launcher plus a few lines that load the adapters.
3. Copy [`rg40xx-h-patch/GrainBernik Buttons Setup.sh`](rg40xx-h-patch/) (and optionally `GrainBernik Audio Check.sh`) into `/userdata/roms/ports/`.
4. Launch GrainBrick from PORTS. On the first launch a short button setup screen appears: press each button it asks for (A, B, X, Y, L1, R1, L2, R2, SELECT, START, MENU, D-pad, then optionally L3/R3 for TAB−/TAB+). Optional steps are skipped automatically after a few seconds.

**Updating an existing GrainBernik installation:** to add Advanced Settings, copy just `gb_advanced.py`, `gb_advanced_controls.py` and the updated `gb_launch.py` into its `grainbrick-beta/` folder. Keep your existing `gb_buttons.json`, `settings.json`, `sound_state.json`, samples, projects and recordings. Existing audio/display/button adapters and USB helper scripts do not need replacing for this update. Make a backup of your current launcher and configuration before copying.

### Buttons

GrainBrick reads the raw button numbers of the TrimUI Brick, so on other devices the button names in the app's hints don't match the physical buttons. `gb_buttons.py` records your device's layout once (saved to `grainbrick-beta/gb_buttons.json`) and translates every button press into the Brick's numbers. After that the button labelled **A** on the RG40XX H is **A** in GrainBrick, **L1** is **L1**, and so on. D-pad buttons are converted to the D-pad events the app expects; analog L2/R2 triggers are supported.

To redo the setup, run **GrainBernik Buttons Setup** from PORTS (or delete `gb_buttons.json`). Set `GRAINBRICK_BUTTONS=0` to turn the adapter off.

### Advanced Settings

Open **SETTINGS**, select **ADVANCED SETTINGS**, then press **A** or **D-pad Right**. Four submenus configure **Left Stick**, **Right Stick**, **L2 Button** and **R2 Button** independently. D-pad Up/Down selects a row; Left/Right or A changes its value; B goes back. Disabled controls stay editable and keep their assignments. Stick Options scrolls when needed; Reset to Defaults requires confirmation and resets only these extra controls.

**START** plays/stops without closing the menu. **L1/R1** switches the main tabs and closes the submenu; edited assignments are already saved and remain available when you return. Navigation hints, contextual help for each setting, reset confirmation and save errors follow the native **INFO LANGUAGE** setting (**EN/RU**) immediately; effect and parameter names retain the app's English naming.

- **Sticks:** separate X/Y parameter assignments, including None; 12% default deadzone; sensitivity, X/Y inversion, Spring/Latch and time-based smoothing. The list is filtered using the running engine's real parameter bounds. Default physical axis indices are left 0/1 and right 2/3; Stick Options allows correcting them for a different controller layout. Calibrated analog-trigger axes are reserved.
- **L2/R2:** independently choose **Hold** or **Toggle**, and **Freeze**, **Reverse**, **Delay Throw**, **Reverb Wash**, **Pitch Drop**, **Bypass**, **ORBIX** or **None**. These are reversible presets of existing engine parameters. Freeze uses native **Motion Hold** fragments, Reverse uses native Motion Reverse, and Bypass bypasses the delay/reverb/shimmer, tape, compressor and EQ processing while preserving sample/grain playback. ORBIX enables the native generator and restores its previous enable state on deactivation; it does not automatically change transport playback.
- **Settings:** automatically saved under `grainbernik_advanced` in the existing `settings.json`; native app settings are preserved. All assignments start OFF. Turning a control OFF retains its selected parameters. Read/write failures are shown in the advanced menu.
- **Scope:** assignments operate on the GRAIN, FX, TAPE and VISUAL tabs. Browsing samples, Settings, Save, help/button rebinding, loss of focus, controller removal and exit release temporary effects. Spring returns to the gesture's initial value; Latch retains the last value at center until the control is disabled or a non-performance screen is entered. Returning from a menu requires a fresh button press or centered stick.
- **Available XY parameters in beta 1.0:** Grain Position/Size/Density/Pitch/Spray; Delay Time/Feedback/Mix/Lowpass; Reverb Mix/Size/Decay; Shimmer Amount/Pitch; Roam Speed; Tape Saturation/Wow/Flutter. Grain and motion parameters require their respective native processing modes to be active.
- **ORBIX XY:** Gravity, Rotation, Bounce, Volume, Attack, Release, Reverb, Balls, Root, Scale, Instrument, Octave and Shape. Counts and musical selections are published as integers. XY changes do not silently enable ORBIX: turn it on natively or assign ORBIX to L2/R2, then use START for playback. All **31** XY choices are filtered against the running engine.
- **Limits:** the current public ParameterBus does not expose Filter Cutoff/Resonance, Tape Speed or Pan. No direct Stutter, Tape Stop or Glitch API was verified, so these are **not offered**. Delay Throw/Reverb Wash are parameter presets, not a new send/return routing system. Original closed application/DSP files remain unmodified.

Detailed behavior, test commands and the on-device checklist: [Advanced Settings](docs/ADVANCED_SETTINGS.md). Set `GRAINBERNIK_ADVANCED=0` to disable this adapter.

### USB audio

- **Output** works out of the box: connect a class-compliant USB audio device *before* starting GrainBrick and choose it in the app's OUTPUT setting.
- **Recording**: GrainBrick records "USB AUDIO" from a fixed device (`hw:1,0`, exactly 48 kHz / 16 bit / stereo), which on the RG40XX H is usually not the USB card and rejects devices with other formats. `gb_audio.py` redirects that recording to the first USB card that can record, through ALSA `plughw`, so sample rate, bit depth and channel count are converted automatically. Choose **USB AUDIO** as the input source on the recording page.
- The RG40XX H has no built-in microphone, so the BUILT-IN MIC source does not work.
- Tested with a **Zoom H1n**: micro-USB to USB-C data cable into the OTG port, on the recorder choose *Audio Interface → PC/Mac*. Batteries in the H1n make the connection more reliable.
- An iPhone cannot be used as a USB sound card on Linux.
- If a device doesn't show up, run **GrainBernik Audio Check** from PORTS with it connected; it writes `grainbrick-beta/audio_check.txt` with what the system sees.
- Optional: `GRAINBRICK_USB_IN=plughw:CARD=<id>,DEV=0` forces the capture device, `GRAINBRICK_AUDIO=0` turns the adapter off.

Optional settings (environment variables, can be added to `GrainBrick beta 1.0.sh` before the `python3` line):

| Variable | Values | Meaning |
|---|---|---|
| `GRAINBRICK_SCREEN` | e.g. `640x480` | Force the real screen size (default: auto-detect) |
| `GRAINBRICK_SCALE` | `smooth` / `fast` | Scaling quality. `smooth` is the default and switches to `fast` automatically if the CPU is too slow |
| `GRAINBRICK_FIT` | `0` | Turn the adapter off |
| `GRAINBERNIK_ADVANCED` | `0` | Disable the Advanced Settings/control adapter |

The launcher log `grainbrick-beta/beta_port_launcher.log` contains a `GB DISPLAY FIT:` line with the detected sizes.

## Установка на RG40XX H (кратко)

Установите официальный релиз в `roms/ports`, затем скопируйте `gb_display_fit.py`, `gb_buttons.py`, `gb_audio.py`, **`gb_advanced.py`, `gb_advanced_controls.py`** и `gb_launch.py` из папки `rg40xx-h-patch/grainbrick-beta/` в `roms/ports/grainbrick-beta/` с заменой, а `GrainBernik Buttons Setup.sh` — в `roms/ports/`. Интерфейс будет уменьшен с 1024×768 до 640×480 на весь экран. При первом запуске появится экран настройки кнопок: нажимайте кнопки, которые он просит. После этого названия кнопок в подсказках приложения совпадут с надписями на приставке. Повторить настройку можно через порт «GrainBernik Buttons Setup». USB-звук: подключите USB-звуковую карту до запуска (проверено с Zoom H1n в режиме Audio Interface → PC/Mac), выберите её в OUTPUT, а для записи — источник USB AUDIO.

### Расширенные настройки

Внутри программы: **SETTINGS → ADVANCED SETTINGS**. Это новый пункт существующих настроек, а не отдельный порт. В нём четыре независимых подменю: **Left Stick**, **Right Stick**, **L2 Button**, **R2 Button**. Все четыре назначения изначально выключены. Крестовина вверх/вниз выбирает строку, влево/вправо или A меняют значение, B возвращает назад. Выключенные элементы приглушены, но доступны для настройки. Сброс этих настроек требует подтверждения.

Стикам назначаются отдельные параметры X/Y или None. Есть мёртвая зона (по умолчанию 12%), чувствительность, инверсия осей, сглаживание и режимы Spring/Latch. Spring возвращает значение к началу жеста, Latch оставляет последнее значение после отпускания стика. В Stick Options также можно поменять номера физических осей, если стандартные 0/1 и 2/3 не подходят устройству.

L2/R2 поддерживают Hold/Toggle и назначения **Freeze, Reverse, Delay Throw, Reverb Wash, Pitch Drop, Bypass, None**. Это управление существующими параметрами: Freeze — штатное удержание фрагментов Motion Hold, Reverse — Motion Reverse; Bypass отключает эффекты, сохраняя воспроизведение. Отдельные Stutter/Tape Stop/Glitch, Filter Cutoff/Resonance, Tape Speed и Pan не добавлены: рабочего доступа к ним в текущей шине не найдено. Список XY включает только реально доступные параметры гранулятора, delay, reverb, shimmer и tape, а также Roam Speed.

**Теперь доступен ORBIX:** для X/Y добавлены Gravity, Rotation, Bounce, Volume, Attack, Release, Reverb, Balls, Root, Scale, Instrument, Octave и Shape. Дискретные параметры меняются целыми значениями. На L2/R2 можно назначить **ORBIX** в Hold/Toggle: кнопка включает генератор и затем возвращает его прежнее состояние. START отдельно управляет воспроизведением.

**Исправлено управление в подменю:** START запускает/останавливает воспроизведение, L1/R1 переключают основные вкладки с сохранением назначений. Подсказки выбранного пункта, кнопок, подтверждения сброса и ошибки сохранения следуют настройке **INFO LANGUAGE: EN/RU**. [Полная русская инструкция](README_RU.md).

Настройки автоматически сохраняются в существующий `settings.json`, в раздел `grainbernik_advanced`. Выключение не стирает назначения. Управление действует на вкладках GRAIN/FX/TAPE/VISUAL. При входе в браузер, настройки, сохранение или справку, при потере фокуса, отключении контроллера и выходе временные эффекты снимаются, включая Toggle/Latch. После возвращения нужна новая кнопка или возврат стика в центр.

**Работа первой версии подтверждена владельцем на RG40XX H с KNULLI 3 ноября 2026 года**. Текущая версия проверяется **36 автотестами**: 21 логическим и 15 с настоящим ARM64-приложением и оригинальным DSP. Новые назначения ORBIX, исправления START/L1/R1 и перевод подсказок требуют повторной проверки на консоли. [Подробный сценарий](docs/ADVANCED_SETTINGS.md).

Для обновления уже установленного GrainBernik достаточно скопировать **`gb_advanced.py`, `gb_advanced_controls.py` и обновлённый `gb_launch.py`**. Существующие адаптеры звука/кнопок/экрана, USB-скрипты, настройки, сэмплы, проекты и записи сохраняйте. Перед заменой сделайте резервную копию загрузчика и настроек.

---

*Original README of GrainBrick below.*

# GrainBrick

A free granular ambient sound instrument for TrimUI Brick.

GrainBrick turns audio samples into evolving, organic textures with granular processing, tape-style sound shaping, effects and the ORBIX generative note engine.

It is designed for hands-on ambient exploration and sound design - not a tracker, sequencer or traditional looper.

## GrainBrick beta 1.0

This is the first public beta for the original TrimUI Brick running KNULLI.

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
2. Copy both grainbrick-beta/ and GrainBrick beta 1.0.sh to the Brick's /userdata/roms/ports/ directory.
3. Refresh your PORTS list in KNULLI.
4. Launch GrainBrick beta 1.0.

When upgrading, preserve your own samples, projects, recordings and settings. Do not delete your existing grainbrick-beta/ folder without backing them up.

## Feedback

This is a beta release. Please use the repository's Issues section to report reproducible bugs and hardware compatibility findings, including your OS version and device model.

## Licensing

GrainBrick is free to download, but its original application source code is currently closed. An open public beta does not mean that the GrainBrick source code is open source.

The distribution includes notices and applicable source materials for its bundled third-party components, including LGPL-licensed SoundTouch. See THIRD_PARTY_NOTICES.md, THIRD_PARTY_LICENSES/ and THIRD_PARTY_SOURCES/ inside the downloadable release.
