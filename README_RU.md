# GrainBernik

[English](README.md) | [Русский](README_RU.md)

**GrainBernik** — неофициальная надстройка для гранулярного эмбиент-инструмента
[GrainBrick](https://github.com/ETRNLIAM/GrainBrick) (ETRNLIAM) для
**Anbernic RG40XX H** с официальной **ROCKNIX**.

Она **не меняет и не распространяет** GrainBrick: закрытое приложение берётся из
вашей копии официального ZIP, а GrainBernik добавляет только запускатель,
адаптеры и USB-аудио.

| У вас | Берите GrainBernik | Описание |
|---|---|---|
| GrainBrick **BETA 2.0** (RHYTHM, ORBIX Rings, OSCILLATOR, LIVE, GRAIN 2/3) | **v0.3.x** (эта страница) | ниже |
| GrainBrick beta **1.0.1** | v0.2.x | [docs/LEGACY_1_0_1_RU.md](docs/LEGACY_1_0_1_RU.md) |

## Что GrainBernik 0.3 добавляет к GrainBrick BETA 2.0

- **RG40XX H как двусторонняя USB-звуковая карта для iPhone.** GrainBrick звучит
  одновременно в наушниках и в iPhone, а звук iPhone можно записывать и
  обрабатывать (SAMPLE → запись, LIVE → USB-вход). Внешние USB-устройства
  (M-VAVE FM1, Zoom H1n) работают как и раньше.
- **STICKS & BUTTONS.** Оба стика (X/Y), L2/R2 и нажатия на стики L3/R3 — это
  независимые органы управления звуком: 61 параметр для стиков, 29 эффектов на
  кнопки, 11 пресетов и один пользовательский слот — в том числе для **RHYTHM**,
  **ORBIX Rings**, **OSCILLATOR**, **LIVE** и **GRAIN 2/3**.
- **Как в самом приложении.** Обе страницы работают по схеме *Console Controls*
  BETA 2.0 (A — войти/править, B — назад, LEFT/RIGHT — изменить, **удерживать
  A + LEFT/RIGHT** — быстрая правка), есть русский и английский (язык INFO).
- **Запуск на ROCKNIX.** Отдельные Python 3.12 + pygame, режим CPU performance во
  время работы, корректный выход по **Select + Start**, подписи кнопок A/B и X/Y
  как на корпусе.

## Что нужно

- Anbernic **RG40XX H** с официальной **ROCKNIX 20261101** (образ DDR4) —
  подготовка SD-карты, Wi-Fi и SSH описаны
  [здесь](docs/LEGACY_1_0_1_RU.md#установка-на-rocknix-рекомендуется). Режим iPhone
  требует ROCKNIX (ядро KNULLI USB-звуковую карту не поддерживает).
- Официальный **`GrainBrick_BETA_2_0.zip`** из
  [релизов GrainBrick](https://github.com/ETRNLIAM/GrainBrick/releases)
  (тег `v2.0.0-beta.2`). Не «Source code» с GitHub.
- ПК с Python 3 и `scp`/`ssh`. Консоли один раз нужен интернет (установщик
  скачивает Python 3.12 и pygame с проверкой SHA-256).

## Установка на ROCKNIX

1. **Соберите пакет** на ПК (Linux / WSL / macOS; в Windows — через WSL):
   ```sh
   sh rocknix/make_package.sh /path/to/GrainBrick_BETA_2_0.zip grainbernik-rocknix
   ```
   Он объединяет официальное приложение, адаптеры GrainBernik, запускатель и
   готовые модули USB-звука. (Файлы официального приложения не публикуйте.)
2. **Скопируйте и установите** (пароль по умолчанию `rocknix`):
   ```sh
   scp -r grainbernik-rocknix root@<ip-консоли>:/storage/
   ssh root@<ip-консоли> "sh /storage/grainbernik-rocknix/install.sh"
   ```
3. **Перезапустите меню:** `ssh root@<ip-консоли> systemctl restart essway`
   (или Start → Quit → Restart EmulationStation). **GrainBrick BETA 2.0**
   появится в разделе **PORTS**.

Куда ставится: приложение — `/storage/roms/ports/grainbrick-beta2/`, запускатель
`GrainBrick BETA 2.0.sh` рядом, Python — `/storage/grainbrick-python`, файлы
USB-звука — `/storage/uac2`. Установка 1.0.1 (`grainbrick beta 1.0.1/`) не
затрагивается, обе версии могут стоять рядом.

**Обновление** — соберите новый пакет и снова запустите `install.sh`.
Сохраняются `samples`, `projects`, `recordings`, `settings.json` (в нём же
STICKS & BUTTONS), `gb_usb_audio.json` и остальные файлы состояния. При первой
установке поверх 1.0.1 переносится `gb_usb_audio.json`; сэмплы и проекты из 1.0.1
скопируйте вручную, если они нужны в BETA 2.0.

**Удаление** — удалите `/storage/roms/ports/grainbrick-beta2/` и
`/storage/roms/ports/GrainBrick BETA 2.0.sh` (сначала сохраните samples/projects);
`/storage/uac2` и `/storage/grainbrick-python` тоже можно удалить.

## Управление (BETA 2.0 «Console Controls»)

| Действие | Кнопки |
|---|---|
| Войти в меню / начать правку поля | **A** |
| Выйти / закончить правку | **B** |
| Изменить значение во время правки | **LEFT / RIGHT** |
| Быстро изменить без входа в правку | удерживать **A**, нажать **LEFT/RIGHT**, отпустить **A** |
| Переключить вкладки | **L1 / R1** |
| Выйти из GrainBrick | **Select + Start** |

На ROCKNIX запускатель меняет местами A/B и X/Y для GrainBrick, чтобы подписи
совпадали с корпусом.

## IPHONE / USB AUDIO

**SETTINGS →** прокрутите до **IPHONE / USB AUDIO** → **A**.

| Строка | Значение |
|---|---|
| MODE | **OFF** · **USB INTERFACE** (внешняя USB-карта) · **IPHONE** (консоль — звуковая карта для iPhone) |
| SEND TO IPHONE | GrainBrick звучит в наушниках/динамике **и** в iPhone |
| RECORD FROM IPHONE | звук iPhone как USB-вход для записи и LIVE |
| STATUS | `CONNECT IPHONE` / `IPHONE CONNECTED` / `PRESS A` (перезапуск гаджета) |

1. Выберите **MODE → IPHONE** (режим USB-звука включается сам, SSH не нужен).
2. Подключите iPhone к USB-C порту OTG консоли кабелем USB-C с передачей данных.
   Статус станет **IPHONE CONNECTED**.
3. **Консоль → iPhone:** в приложении на iPhone (Диктофон, GarageBand, камера)
   выберите консоль как источник звука.
4. **iPhone → консоль:** включите звук на iPhone; в GrainBrick в
   **SAMPLE → запись** или **LIVE** выберите вход **USB**. Мониторинг — штатный
   в BETA 2.0 (экран записи).
5. **MODE → OFF** возвращает обычный USB-режим ROCKNIX.

*Внешние USB-устройства (FM1, Zoom H1n):* оставьте режим **OFF** или **USB
INTERFACE** и подключите устройство — оно определяется как в штатном приложении.

iOS может показать *«Аксессуару требуется слишком много энергии»*: консоль питается
по кабелю. Звук при этом работает; предупреждение убирает USB-C хаб со сквозной
зарядкой PD. Технические подробности: [docs/USB_AUDIO.md](docs/USB_AUDIO.md).

## STICKS & BUTTONS

**SETTINGS →** последняя строка **STICKS & BUTTONS** → **A**. В строке показан
активный пресет (`NONE`, имя пресета или `USER`), а описание объясняет пункт под
курсором. По умолчанию всё выключено (**OFF**).

**Главная страница:** Left Stick · Right Stick · L2 Button · R2 Button ·
L3 Click · R3 Click · Preset · Reset to Defaults · Back.

- **Стики:** *Enabled*, *X Effect*, *Y Effect* (61 параметр, см. ниже) и *Stick
  Options*: мёртвая зона, чувствительность, инверсия X/Y, **Spring** (возврат к
  начальному значению) или **Latch** (значение остаётся), сглаживание, физические
  оси.
- **L2 / R2 / L3 / R3:** *Enabled*, *Effect*, *Mode* — **Hold** (пока нажато) или
  **Toggle** (нажали — включено, ещё раз — выключено). Для L3/R3 по умолчанию
  Toggle; эффекты *Step* меняют значение один раз за нажатие и оставляют его.
- **Preset:** выберите пресет → подтвердите **A**. *Save User* / *Load User* хранят
  одну личную раскладку. Пресеты меняют только назначения, не звук.
  **Если изменить любое назначение, активным пресетом станет `USER`.**

**Что можно назначить**

| Группа | Параметры стиков (примеры) |
|---|---|
| GRAIN, GRAIN 2/3 | position, size, density, pitch, spray, разброс высоты, случайность размера/тайминга, шанс реверса, envelope; roam speed/range/wander |
| FX, TAPE | delay time/feedback/mix/lowpass, reverb mix/size/decay/damp, shimmer mix/pitch/feedback, tape saturation/wow/flutter/hiss |
| ORBIX | gravity, rotation, bounce, volume, attack, release, reverb, balls, root, scale, instrument, octave, shape |
| **ORBIX Rings** | structure, brightness, damping, position, mix, tune, detune, stereo, noise, excite mix |
| **OSCILLATOR** | blend, dry/wet, drive, X-mod, баланс A/B, level |
| **RHYTHM / LIVE** | темп BPM и offset, уровень входа, мастер-уровень |

| Эффект кнопки | Что делает |
|---|---|
| Freeze, Reverse, Stutter | штатные Motion hold / reverse / jump+chaos |
| Delay Throw, Reverb Wash, Shimmer Burst | временное усиление задержки / реверба / шиммера |
| Pitch Drop, Octave Up | ∓1 октава (относительно, суммируется) |
| Octave +, Octave − | **шаг**: каждое нажатие сдвигает на октаву и оставляет |
| Grain Burst, Scatter, Reverse Grains | плотное облако / разброс высоты-размера-тайминга / зёрна задом наперёд |
| Lo-Fi, Bypass, ORBIX | tape + 8 бит / FX и EQ выключены / ORBIX включён |
| **Rings Bloom, Rings Damp, Rings Detune** | открытый яркий звон / заглушить резонанс / расстройка и широкое стерео |
| **Osc On, Osc Drive, Osc FM** | осциллятор вкл / сильный драйв / сильная кросс-модуляция |
| **Slow Down, Speed Up** | темп ∓20 BPM пока держите; прежний темп возвращается |
| **Tempo +5, Tempo −5** | **шаг**: темп ±5 BPM за нажатие |
| **Input Cut, Input Boost, Mute Out** | вход LIVE на минимум / +6 dB / мьют мастера, пока держите |

**Пресеты** (левый стик X/Y · правый стик X/Y · L2 · R2 · L3 · R3):

| Пресет | Левый | Правый | L2 | R2 | L3 | R3 |
|---|---|---|---|---|---|---|
| Granular | Position / Size | Pitch / Density | Freeze | Reverse | Octave − | Octave + |
| Ambient | Position / Spray | Reverb / Shimmer | Freeze | Reverb Wash | Shimmer Burst | Bypass |
| Texture | Size / Spray | Density / Roam Speed | Grain Burst | Freeze | Reverse | Stutter |
| Echo | Delay Time / Feedback | Delay Mix / Reverb Mix | Delay Throw | Reverb Wash | Freeze | Bypass |
| Tape | Saturation / Wow | Pitch / Flutter | Pitch Drop | Lo-Fi | Reverse | Bypass |
| ORBIX Play | Rotation / Gravity | Bounce / Reverb | ORBIX | Reverb Wash | Freeze | Shimmer Burst |
| **Rhythm** | Position / Size | Density / Pitch | Slow Down | Speed Up | Tempo −5 | Tempo +5 |
| **Rings** | Structure / Brightness | Damping / Position | Rings Bloom | Rings Damp | ORBIX | Rings Detune |
| **Oscillator** | Blend / Drive | X-Mod / Dry-Wet | Osc FM | Osc Drive | Osc On | Bypass |
| **Live** | Position / Input Level | Density / Spray | Input Cut | Mute Out | Freeze | Grain Burst |
| **Grain 2/3** | Size Random / Timing Random | Pitch Spread / Reverse Chance | Scatter | Reverse Grains | Freeze | Octave + |

**Полезно знать**

- Органы работают на вкладках **GRAIN, FX, TAPE и VISUAL**; на других экранах
  L2/R2 остаются приложению. Пока L3/R3 **включены**, нажатия на стики не
  переключают вкладки. Toggle-эффекты остаются включёнными при смене вкладок и
  снимаются повторным нажатием, при открытии страницы или выходе.
- Если два эффекта меняют один параметр, побеждает нажатый последним;
  относительные (Octave Up, Pitch Drop, Slow/Speed Up, Input Boost) складываются.
- Параметры паттернов RHYTHM находятся внутри самого RHYTHM, а не в общем списке
  параметров, поэтому назначается только общий **темп**. Hold на темпе борется с
  LINK и tap-темпом, пока нажат.
- Настройки хранятся в `settings.json` (`grainbernik_advanced`); назначения из
  версии для 1.0.1 подхватываются (параметры, которых больше нет, становятся *None*).
- Полное описание: [docs/STICKS_AND_BUTTONS.md](docs/STICKS_AND_BUTTONS.md).

## Чего в 0.3 ещё нет

- Сокращённого меню SETTINGS (AUDIO / CONTROLS) и **удаления записей прямо в
  SAMPLE** из линии 1.0.1 — запланировано (шаг «2b» в
  [docs/BETA2_PORT.md](docs/BETA2_PORT.md)).
- Ещё не измерено на H700: нагрузка на CPU резонатора **Rings** и **LIVE** на
  высоких настройках; **Bluetooth MIDI** на ROCKNIX; одновременная работа iPhone и
  USB MIDI-хоста на единственном OTG-порту.
- KNULLI запускатель BETA 2.0 не поддерживает (режим iPhone там всё равно
  невозможен); используйте штатную инструкцию автора для KNULLI.

## Если что-то не работает

| Проблема | Что делать |
|---|---|
| GrainBrick BETA 2.0 нет в PORTS | `systemctl restart essway`; проверьте `/storage/roms/ports/GrainBrick BETA 2.0.sh` |
| Чёрный экран / возврат в меню | прочитайте `/storage/roms/ports/grainbrick-beta2/gb_launch.log` (строки `GRAINBERNIK ADAPTER FAILED` / `GB ADVANCED` / `GB USB AUDIO`) |
| Нет строки STICKS & BUTTONS или IPHONE | адаптер не загрузился: смотрите журнал; `GRAINBERNIK_ADVANCED=0` / `GRAINBERNIK_USB_AUDIO=0` их отключают |
| Статус остаётся `CONNECT IPHONE` | кабель USB-C с данными в порт OTG, нажмите **A** на строке STATUS, затем переподключите |
| Нет звука | проверьте строки AUDIO OUTPUT и OUTPUT BOOST в SETTINGS и MODE на странице iPhone |
| Диагностика | `sh /storage/grainbernik-rocknix/gb-diag.sh` |

## Параметры

Добавьте строки `export ИМЯ=значение` в `GrainBrick BETA 2.0.sh` перед строкой с Python.

| Переменная | Значения | Смысл |
|---|---|---|
| `GRAINBERNIK_ADVANCED` | `0` | Отключить STICKS & BUTTONS |
| `GRAINBERNIK_USB_AUDIO` | `0` | Отключить адаптер iPhone / USB-звука |
| `GRAINBERNIK_SWAP_ABXY` | `1` / `0` | Поменять A/B и X/Y для GrainBrick (по умолчанию 1) |
| `GRAINBRICK_DISPLAY_FILTER` | `smooth` / `fast` | Масштабирование экрана (по умолчанию `smooth`) |

Тесты: `GRAINBRICK_BETA2_ZIP=/path/to/GrainBrick_BETA_2_0.zip python3 -m pytest tests`
(нативные ARM64-тесты на других машинах пропускаются).

## Сборка модулей USB-звука

Готовые `u_audio.ko` и `usb_f_uac2.ko` для ROCKNIX 20261101 (ядро 7.2.0) лежат в
[`rocknix/uac2/`](rocknix/uac2/); как они собраны и как пересобрать:
[docs/LEGACY_1_0_1_RU.md](docs/LEGACY_1_0_1_RU.md#сборка-модулей-usb-звука).

## Лицензия

В репозитории только собственные файлы GrainBernik, кода GrainBrick здесь нет.
GrainBrick бесплатен, но **не open source**; его уведомления и сторонние лицензии
(SoundTouch, Mutable Instruments Rings, NumPy) — в официальном пакете. Файлы
официального приложения не распространяйте.
