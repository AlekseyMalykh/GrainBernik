# GrainBernik

[English](README.md) | Русский

**GrainBernik** — неофициальный патч [GrainBrick](https://github.com/ETRNLIAM/GrainBrick)
(инструмент для гранулярного эмбиента) для **Anbernic RG40XX H** (экран 640×480).

Главное:

- **RG40XX H — двусторонняя USB-звуковая карта для iPhone** (ROCKNIX):
  GrainBrick звучит одновременно в наушниках консоли **и** в iPhone, звук с
  iPhone записывается в SAMPLE, есть мониторинг входа. Примерно как Akai MPC
  Sample с iPhone.
- **Стики и кнопки**: левый/правый стик по X/Y, L2/R2 и нажатия на стики
  L3/R3 — независимые органы управления звуком, 6 пресетов.
- **Удаление записей** прямо в браузере SAMPLE.
- Раскладка и подписи кнопок RG40XX H.

Патч не изменяет и не распространяет закрытое приложение GrainBrick: нужен
официальный `grainbrick.beta.1.0.1.zip` от автора.

> **Статус (6 ноября 2026):** проверено на RG40XX H с **официальным ROCKNIX
> 20261101 (образ DDR4)** и **iPhone 16**: звук в наушники + iPhone, запись с
> iPhone, мониторинг, L3/R3, пресеты и удаление записей работают. На KNULLI всё
> работает как раньше, но режим USB-звуковой карты его ядро не поддерживает
> (см. [Почему ROCKNIX](#почему-rocknix-для-iphone)).

## Содержание

- [Установка на ROCKNIX (рекомендуется)](#установка-на-rocknix-рекомендуется)
- [iPhone / USB-звук](#iphone--usb-звук)
- [Удаление записей](#удаление-записей)
- [Стики и кнопки](#стики-и-кнопки)
- [Кнопки](#кнопки)
- [Установка на KNULLI](#установка-на-knulli)
- [Сборка модулей USB-звука](#сборка-модулей-usb-звука)
- [Параметры](#параметры)

## Установка на ROCKNIX (рекомендуется)

1. **ROCKNIX.** Запишите официальный `ROCKNIX-H700.aarch64-20261101-DDR4.img.gz`
   ([релизы](https://github.com/ROCKNIX/distribution/releases)) через Raspberry
   Pi Imager. На разделе **ROCKNIX** скопируйте
   `device_trees/sun50i-h700-anbernic-rg40xx-h.dtb` в корень и переименуйте
   копию в `dtb.img`. На нашей RG40XX H образ DDR3 не запускается.
   В меню ROCKNIX подключите Wi-Fi и включите SSH.
2. **Пакет.** На компьютере с Python 3 (Linux, WSL, macOS):
   ```sh
   sh rocknix/make_package.sh /путь/к/grainbrick.beta.1.0.1.zip grainbernik-rocknix
   ```
   Скрипт собирает вместе официальное приложение, патч GrainBernik,
   запускалку для ROCKNIX и готовые модули USB-звука.
3. **Копирование и установка** (пароль `rocknix`):
   ```sh
   scp -r grainbernik-rocknix root@<ip-консоли>:/storage/
   ssh root@<ip-консоли> sh /storage/grainbernik-rocknix/install.sh
   ```
   Установщик один раз скачивает Python 3.12 (python-build-standalone) и
   pygame 2.6.1 в `/storage/grainbrick-python` (с проверкой SHA-256),
   подключает SDL2 из ROCKNIX, копирует GrainBrick в `/storage/roms/ports`, а
   файлы USB-звука — в `/storage/uac2`. Системные файлы ROCKNIX не меняются.
4. Перезапустите меню (`systemctl restart essway`) — в **PORTS** появится
   **GrainBrick beta 1.0.1**. Для обновления соберите пакет заново,
   скопируйте и снова запустите `install.sh`: сэмплы, проекты и настройки
   сохраняются. Перезагружать консоль не нужно.

Пока GrainBrick открыт, процессор работает в режиме `performance`.

## iPhone / USB-звук

**SETTINGS → IPHONE / USB AUDIO:**

| Пункт | Что делает |
|---|---|
| MODE | **OFF** · **USB INTERFACE** (внешняя USB-звуковая карта, например Zoom H1n) · **IPHONE** (консоль — звуковая карта для iPhone) |
| SEND TO IPHONE | GrainBrick звучит в наушниках/динамике **и** в iPhone |
| RECORD FROM IPHONE | запись звука iPhone в SAMPLE |
| MONITOR WHILE RECORDING | слышать iPhone в наушниках во время записи |
| STATUS | `CONNECT IPHONE (USB-C)` / `IPHONE CONNECTED` / `NOT STARTED - PRESS A` |

При выборе **IPHONE** USB-звук включается сам, SSH не нужен; **OFF**
возвращает обычный USB-режим ROCKNIX.

1. Подключите iPhone к разъёму USB-C (OTG) консоли кабелем USB-C ↔ USB-C.
2. **Консоль → iPhone:** в приложении на iPhone (Диктофон, GarageBand…) входом
   становится консоль; GrainBrick звучит в наушниках и в iPhone.
3. **iPhone → консоль:** включите звук на iPhone, в GrainBrick откройте
   **SAMPLE → Y RECORD → USB AUDIO** и нажмите **A**.
4. **Мониторинг:** во время записи с iPhone его звук слышен в наушниках
   консоли (обратно в iPhone не уходит). **SELECT во время записи**
   включает/выключает мониторинг, выбор запоминается.
5. При вставленных наушниках динамик выключается (на этой консоли ROCKNIX сам
   этого не делает).

iOS пишет *«Аксессуар использует слишком много энергии»*: контроллер питания
консоли берёт ток из iPhone (в этом режиме ограничен минимумом 100 мА). Звук
работает, но iOS может разорвать соединение. **USB-C хаб с проходной зарядкой
(PD)** между iPhone и консолью убирает предупреждение.

Технически: стерео, 16 бит, 48 кГц в обе стороны (Linux `f_uac2`). Маршруты
строит PipeWire: общий выход `gb_both` (наушники + iPhone с подстройкой
частот), запись со входа USB-карты, мониторинг через `pw-loopback`.
Не останавливайте PipeWire — на ROCKNIX через него идёт и встроенный звук.

### Почему ROCKNIX для iPhone

Ядро KNULLI (Allwinner BSP 4.9) не может привязать функцию UAC2
(`afunc_bind`: нет изохронной конечной точки IN). В ROCKNIX — Linux 7.2 с
драйвером MUSB, режим USB-устройства в нём работает. UAC2 в ядро не встроен,
поэтому GrainBernik загружает два внешних модуля (`rocknix/uac2/`). История
неудачной попытки с самосборным образом:
[`tools/legacy-rocknix-test-image/`](tools/legacy-rocknix-test-image/).

## Удаление записей

В **SAMPLE** откройте папку **RECORDINGS** и выберите запись — внизу появится
`SELECT: УДАЛИТЬ ЗАПИСЬ`. Нажмите **SELECT**, затем **ещё раз SELECT** в
течение 4 секунд (`SELECT ЕЩЁ РАЗ: УДАЛИТЬ имя`). Удалять можно только WAV из
`samples/recordings`; **загруженная** (играющая) запись защищена; демо-сэмплы и
другие папки не трогаются — там SELECT, как и раньше, открывает справку.

## Стики и кнопки

**SETTINGS → STICKS & BUTTONS** (бывшие Advanced Settings): шесть независимых
органов, все по умолчанию **OFF** — **Left Stick**, **Right Stick** (параметры
по X/Y), **L2**, **R2**, **L3 Click**, **R3 Click** (эффекты).

- **Стики:** любой из 31 параметра движка на каждую ось, мёртвая зона,
  чувствительность, инверсия, Spring/Latch, сглаживание, номер оси.
- **Эффекты кнопок:** Freeze, Reverse, Delay Throw, Reverb Wash, Pitch Drop,
  Octave Up, Shimmer Burst, Grain Burst, Lo-Fi, Stutter, Bypass, ORBIX и шаговые
  **Octave +** / **Octave −**.
- **Режимы:** **Hold** (пока нажата), **Toggle** (нажал — включено, ещё раз —
  выключено; по умолчанию для L3/R3), **Step** (Octave ±: каждое нажатие сдвигает
  высоту зёрен на октаву и оставляет её, в пределах ±24).
- Toggle-эффекты сохраняются при смене вкладок; выключаются повторным
  нажатием, открытием этого меню или выходом. Hold и стики отпускаются вне
  вкладок звука.
- Если эффекты меняют один параметр, побеждает последний нажатый; Pitch
  Drop/Octave Up — относительные и складываются.
- Пока L3/R3 **ON**, нажатия на стики не листают вкладки (в оригинале это
  TAB−/TAB+). Эффекты работают на GRAIN, FX, TAPE и VISUAL.

**Пресеты** (Presets → выбрать → подтвердить; один слот User через Save
Current / Load User):

| Пресет | Левый X / Y | Правый X / Y | L2 | R2 | L3 | R3 |
|---|---|---|---|---|---|---|
| Granular | Position / Size | Pitch / Density | Freeze | Reverse | Octave − | Octave + |
| Ambient | Position / Spray | Reverb Mix / Shimmer | Freeze | Reverb Wash | Shimmer Burst | Bypass |
| Texture | Size / Spray | Density / Roam Speed | Grain Burst | Freeze | Reverse | Stutter |
| Echo | Delay Time / Feedback | Delay Mix / Reverb Mix | Delay Throw | Reverb Wash | Freeze | Bypass |
| Tape | Saturation / Wow | Pitch / Flutter | Pitch Drop | Lo-Fi | Reverse | Bypass |
| ORBIX Play | Rotation / Gravity | Bounce / Reverb | ORBIX | Reverb Wash | Freeze | Shimmer Burst |

Пресеты меняют только назначения, а не параметры звука. Настройки хранятся в
`settings.json` (`grainbernik_advanced`); старый слот User без L3/R3
сохраняется. Подсказки в меню следуют настройке INFO LANGUAGE (EN/RU).
Подробнее: [docs/ADVANCED_SETTINGS.md](docs/ADVANCED_SETTINGS.md).

## Кнопки

- **ROCKNIX:** GrainBrick 1.0.1 сам раскладывает кнопки по базе SDL
  (`H700 Gamepad`). В ROCKNIX кнопки названы по надписям, а GrainBrick ждёт
  названия по положению (как на KNULLI), поэтому запускалка меняет местами a/b
  и x/y — только для GrainBrick. Старый адаптер калибровки `gb_buttons` на
  ROCKNIX **выключен** (он переводил бы кнопки дважды). Отдельные кнопки можно
  переназначить штатно: **SETTINGS → BUTTON MAPPING**.
- **KNULLI:** `gb_buttons.py` запоминает раскладку при первом запуске
  (`gb_buttons.json`); повторить — порт **GrainBernik Buttons Setup**.

## Установка на KNULLI

1. Скопируйте `grainbrick beta 1.0.1/` и `GrainBrick beta 1.0.1.sh` из
   официального ZIP в `/userdata/roms/ports/` (папка `roms/ports` на SHARE).
2. Скопируйте все файлы из [`rg40xx-h-patch/grainbrick-beta/`](rg40xx-h-patch/grainbrick-beta/)
   в `grainbrick beta 1.0.1/` (с заменой `gb_launch.py`), а
   `GrainBernik Buttons Setup.sh` из [`rg40xx-h-patch/`](rg40xx-h-patch/) — в `roms/ports/`.
3. Запустите из PORTS; при первом запуске пройдите настройку кнопок.

На KNULLI работают внешние USB-интерфейсы (например, Zoom H1n в режиме *Audio
Interface*) для вывода и записи; режим iPhone — нет (ограничение ядра, см.
выше). Встроенного микрофона у RG40XX H нет.

## Сборка модулей USB-звука

Готовые `u_audio.ko` и `usb_f_uac2.ko` для ROCKNIX 20261101 (ядро 7.2.0) лежат
в [`rocknix/uac2/`](rocknix/uac2/). Пересборка (Linux/WSL с
`gcc-aarch64-linux-gnu`, консоль доступна по SSH):

```sh
bash rocknix/build/build_uac2_modules.sh
```

Скрипт скачивает Linux 7.2, накладывает патчи ROCKNIX 20261101 для H700, берёт
конфигурацию ядра с консоли, один раз собирает `vmlinux` (10–40 минут) и два
модуля. CRC символов берутся из `rocknix/build/official.symvers`, извлечённого
из официального ядра скриптом `rocknix/build/extract_kcrctab.py`: сборка GCC 13
даёт другие CRC, чем GCC 16 у ROCKNIX. Для другой версии ROCKNIX скопируйте её
`/flash/KERNEL` и создайте `official.symvers` заново.

Вручную на консоли: `sh /storage/uac2/uac2-on.sh` / `sh /storage/uac2/uac2-off.sh`.
Диагностика: `sh /storage/grainbernik-rocknix/gb-diag.sh`.

## Параметры

Переменные окружения (добавить в `GrainBrick beta 1.0.1.sh` перед строкой с Python):

| Переменная | Значения | Действие |
|---|---|---|
| `GRAINBRICK_BUTTONS` | `0` / `1` | Адаптер калибровки кнопок (на KNULLI включён, на ROCKNIX выключен) |
| `GRAINBERNIK_SWAP_ABXY` | `1` / `0` | ROCKNIX: менять a/b и x/y в раскладке SDL (по умолчанию 1) |
| `GRAINBERNIK_ADVANCED` | `0` | Выключить «Стики и кнопки» |
| `GRAINBERNIK_MASK_POLL` | `0` | Не скрывать занятые кнопки от прямого опроса |
| `GRAINBERNIK_SAMPLE_DELETE` | `0` | Выключить удаление записей |
| `GRAINBERNIK_USB_AUDIO` | `0` | Выключить адаптер iPhone / USB-звука |
| `GRAINBERNIK_FIT`, `GRAINBERNIK_LEGACY_AUDIO` | `1` | Старые адаптеры экрана и USB-записи для beta 1.0 |
| `GRAINBRICK_SCREEN`, `GRAINBRICK_SCALE` | например `640x480`, `smooth`/`fast` | Штатные параметры экрана |

Журнал: `grainbrick beta 1.0.1/gb_launch.log`. Тесты:
`python3 -m unittest discover -s tests` (тесты с ARM64-приложением вне консоли
пропускаются).

## Лицензия

GrainBrick распространяется автором бесплатно, исходный код приложения закрыт.
Патч GrainBernik — открытые скрипты и адаптеры; модули ядра собраны из Linux
(GPL-2.0) с патчами ROCKNIX.
