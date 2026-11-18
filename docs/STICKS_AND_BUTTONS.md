# STICKS & BUTTONS — reference (GrainBernik 0.3, GrainBrick BETA 2.0)

[English](#english) · [Русский](#русский)

## English

Open: **SETTINGS →** last row **STICKS & BUTTONS** → **A**. Controls follow the BETA 2.0
*Console Controls*: **A** enters a submenu or starts editing a value (ON/OFF rows flip at once),
**B** leaves (first ends editing), **LEFT/RIGHT** change a value while editing,
**hold A + LEFT/RIGHT** changes the focused value without entering edit mode,
**UP/DOWN** move (the focus stays on a value being edited). **L1/R1** are blocked while the page is open.

The active preset is shown in the SETTINGS row, next to the page title and at the start of the description.
A preset is *active* only while all six controls equal it exactly (stick calibration — deadzone, inversion,
physical axes — is not part of a preset); any other state is `USER`, untouched defaults are `NONE`.

### Stick parameters (61)

| Label | Parameter id | Range |
|---|---|---|
| Grain Position | `grain.position` | 0 … 1 |
| Grain Size | `grain.size` | 0.02 … 2 |
| Grain Density | `grain.density` | 1 … 50 |
| Grain Pitch | `grain.pitch` | -24 … 24 |
| Grain Spray | `grain.spray` | 0 … 1 |
| Grain Pitch Spread | `grain.pitch_spread` | 0 … 12 |
| Grain Size Random | `grain.size_random` | 0 … 100 |
| Grain Timing Random | `grain.timing_random` | 0 … 100 |
| Grain Reverse Chance | `grain.reverse` | 0 … 100 |
| Grain Envelope | `grain.envelope` | 0 … 100 |
| Roam Speed | `roam.speed` | 0.1 … 4 |
| Roam Range | `roam.range` | 0.01 … 1 |
| Roam Wander | `roam.wander` | 0 … 1 |
| Delay Time | `delay.time` | 10 … 2000 |
| Delay Feedback | `delay.feedback` | 0 … 0.95 |
| Delay Mix | `delay.mix` | 0 … 1 |
| Delay Lowpass | `delay.lowpass` | 500 … 20000 |
| Reverb Mix | `reverb.mix` | 0 … 1 |
| Reverb Size | `reverb.size` | 0 … 1 |
| Reverb Decay | `reverb.decay` | 0.3 … 20 |
| Reverb Damp | `reverb.damp` | 500 … 20000 |
| Shimmer Amount | `shimmer.mix` | 0 … 1 |
| Shimmer Pitch | `shimmer.shift` | -24 … 24 |
| Shimmer Feedback | `shimmer.feedback` | 0 … 0.85 |
| Tape Saturation | `tape.saturation` | 0 … 1 |
| Tape Wow | `tape.wow` | 0 … 1 |
| Tape Flutter | `tape.flutter` | 0 … 1 |
| Tape Hiss | `tape.hiss` | 0 … 1 |
| ORBIX Gravity | `orbix.gravity` | 0 … 420 |
| ORBIX Rotation | `orbix.rotation` | -55 … 55 |
| ORBIX Bounce | `orbix.bounce` | 50 … 100 |
| ORBIX Volume | `orbix.volume` | 0 … 100 |
| ORBIX Attack | `orbix.attack` | -40 … 100 |
| ORBIX Release | `orbix.release` | -40 … 40 |
| ORBIX Reverb | `orbix.reverb` | 0 … 100 |
| ORBIX Balls | `orbix.balls` | 1 … 12 |
| ORBIX Root | `orbix.root` | 0 … 11 |
| ORBIX Scale | `orbix.scale` | 0 … 4 |
| ORBIX Instrument | `orbix.instrument` | 0 … 3 |
| ORBIX Octave | `orbix.octave` | -4 … 2 |
| ORBIX Shape | `orbix.shape` | 0 … 5 |
| Rings Structure | `orbix.res.structure` | 0 … 100 |
| Rings Brightness | `orbix.res.brightness` | 0 … 100 |
| Rings Damping | `orbix.res.damping` | 0 … 100 |
| Rings Position | `orbix.res.position` | 0 … 100 |
| Rings Mix | `orbix.res.mix` | 0 … 100 |
| Rings Tune | `orbix.res.tune` | -24 … 24 |
| Rings Detune | `orbix.res.detune` | 0 … 100 |
| Rings Stereo | `orbix.res.stereo` | 0 … 100 |
| Rings Noise | `orbix.res.noise` | 0 … 100 |
| Rings Excite Mix | `orbix.res.excite_mix` | 0 … 100 |
| Osc Blend | `osc.blend` | 0 … 1 |
| Osc Dry/Wet | `osc.dry_wet` | 0 … 1 |
| Osc Drive | `osc.drive` | 0 … 1 |
| Osc X-Mod | `osc.xmod` | 0 … 1 |
| Osc A/B Balance | `osc.balance` | 0 … 1 |
| Osc Level | `osc.level_db` | -12 … 6 |
| Tempo BPM | `tempo.bpm` | 20 … 300 |
| Tempo Offset | `tempo.offset` | -4 … 4 |
| Input Level | `level.input_db` | -24 … 12 |
| Master Level | `level.master_db` | -60 … 6 |

ENUM-like ORBIX values (balls, root, scale, instrument, octave, shape) are rounded to valid integers.

### Button effects (29)

| Effect | Changes | Type |
|---|---|---|
| Freeze | `grain.enabled` 1, `motion.enabled` 1, `motion.hold` 1 | hold / toggle |
| Reverse | `motion.enabled` 1, `motion.reverse` 1 | hold / toggle |
| Delay Throw | `delay.mix` 0.65, `delay.feedback` 0.6 | hold / toggle |
| Reverb Wash | `reverb.mix` 0.85, `reverb.size` 0.95, `reverb.decay` 12 | hold / toggle |
| Pitch Drop | `grain.enabled` 1, `grain.pitch` offset -12 | hold / toggle |
| Bypass | `delay.mix` 0, `reverb.mix` 0, `shimmer.mix` 0, `tape.enabled` 0, `comp.enabled` 0, all six `eq.*` = 0 | hold / toggle |
| ORBIX | `orbix.enabled` 1 | hold / toggle |
| Octave Up | `grain.enabled` 1, `grain.pitch` offset +12 | hold / toggle |
| Shimmer Burst | `shimmer.mix` 0.8, `shimmer.feedback` 0.7 | hold / toggle |
| Grain Burst | `grain.enabled` 1, `grain.density` 32, `grain.spray` 0.6 | hold / toggle |
| Lo-Fi | `tape.enabled` 1, `tape.bit8` 1 | hold / toggle |
| Stutter | `motion.enabled` 1, `motion.jump` 1, `motion.chaos` 1 | hold / toggle |
| Scatter | `grain.enabled` 1, `grain.pitch_spread` 7, `grain.size_random` 60, `grain.timing_random` 50 | hold / toggle |
| Reverse Grains | `grain.enabled` 1, `grain.reverse` 100 | hold / toggle |
| Rings Bloom | `orbix.res.mix` 100, `orbix.res.damping` 15, `orbix.res.brightness` 85 | hold / toggle |
| Rings Damp | `orbix.res.damping` 95, `orbix.res.brightness` 25 | hold / toggle |
| Rings Detune | `orbix.res.detune` 60, `orbix.res.stereo` 100 | hold / toggle |
| Osc On | `osc.enabled` 1 | hold / toggle |
| Osc Drive | `osc.enabled` 1, `osc.drive` 0.9 | hold / toggle |
| Osc FM | `osc.enabled` 1, `osc.xmod` 0.8 | hold / toggle |
| Slow Down | `tempo.bpm` offset -20 | hold / toggle |
| Speed Up | `tempo.bpm` offset +20 | hold / toggle |
| Input Cut | `level.input_db` -24 | hold / toggle |
| Input Boost | `level.input_db` offset +6 | hold / toggle |
| Mute Out | `level.master_db` -60 | hold / toggle |
| Octave + | `grain.enabled` = 1, `grain.pitch` step +12 | step |
| Octave - | `grain.enabled` = 1, `grain.pitch` step -12 | step |
| Tempo +5 | `tempo.bpm` step +5 | step |
| Tempo -5 | `tempo.bpm` step -5 | step |

Hold effects restore the values from before the press. Absolute values: the most recently pressed button wins; offsets add up.

### Presets

| Preset | Left X / Y | Right X / Y | L2 | R2 | L3 | R3 | Sensitivity | Smoothing |
|---|---|---|---|---|---|---|---|---|
| Granular | grain.position / grain.size | grain.pitch / grain.density | Freeze | Reverse | Octave - | Octave + | 70% | 60 ms |
| Ambient | grain.position / grain.spray | reverb.mix / shimmer.mix | Freeze | Reverb Wash | Shimmer Burst | Bypass | 50% | 180 ms |
| Texture | grain.size / grain.spray | grain.density / roam.speed | Grain Burst | Freeze | Reverse | Stutter | 60% | 90 ms |
| Echo | delay.time / delay.feedback | delay.mix / reverb.mix | Delay Throw | Reverb Wash | Freeze | Bypass | 50% | 100 ms |
| Tape | tape.saturation / tape.wow | grain.pitch / tape.flutter | Pitch Drop | Lo-Fi | Reverse | Bypass | 40% | 140 ms |
| ORBIX Play | orbix.rotation / orbix.gravity | orbix.bounce / orbix.reverb | ORBIX | Reverb Wash | Freeze | Shimmer Burst | 50% | 120 ms |
| Rhythm | grain.position / grain.size | grain.density / grain.pitch | Slow Down | Speed Up | Tempo -5 | Tempo +5 | 60% | 80 ms |
| Rings | orbix.res.structure / orbix.res.brightness | orbix.res.damping / orbix.res.position | Rings Bloom | Rings Damp | ORBIX | Rings Detune | 55% | 120 ms |
| Oscillator | osc.blend / osc.drive | osc.xmod / osc.dry_wet | Osc FM | Osc Drive | Osc On | Bypass | 55% | 100 ms |
| Live | grain.position / level.input_db | grain.density / grain.spray | Input Cut | Mute Out | Freeze | Grain Burst | 50% | 100 ms |
| Grain 2/3 | grain.size_random / grain.timing_random | grain.pitch_spread / grain.reverse | Scatter | Reverse Grains | Freeze | Octave + | 60% | 90 ms |

L3/R3 and ORBIX use **Toggle**, L2/R2 use **Hold**. Applying a preset asks for confirmation; the first one archives your current setup into an empty User slot.

### Storage and safety

- `settings.json` → `grainbernik_advanced` (version 1, plus `user_preset`). Unknown or removed parameter ids load as *None*; the rest of `settings.json` is preserved.
- Controls run on GRAIN, FX, TAPE and VISUAL, never while INFO, button mapping, the Bluetooth MIDI page or a project-name edit is open. Leaving those screens releases sticks and Hold effects; Toggle effects stay.
- Buttons are taken from the engine's own input layer (virtual L2 = 10, R2 = 11, L3 = 15, R3 = 16). L3/R3 are owned on every screen while **ON**; L2/R2 only on sound tabs and only with an effect assigned.
- Sticks are read directly; analog trigger axes are excluded automatically.
- Disable the page: `GRAINBERNIK_ADVANCED=0` in `GrainBrick BETA 2.0.sh`.

## Русский

Открыть: **SETTINGS →** последняя строка **STICKS & BUTTONS** → **A**. Управление — *Console Controls* BETA 2.0:
**A** — войти в подменю или начать правку (строки ВКЛ/ВЫКЛ переключаются сразу), **B** — назад (сначала закончить правку),
**LEFT/RIGHT** — изменить значение во время правки, **удерживать A + LEFT/RIGHT** — изменить значение под курсором без входа в правку,
**UP/DOWN** — перемещение (во время правки фокус остаётся на значении). Пока страница открыта, **L1/R1** заблокированы.

Активный пресет показан в строке SETTINGS, рядом с заголовком страницы и в начале описания. Пресет считается активным, только
пока все шесть органов точно ему равны (калибровка стика — мёртвая зона, инверсия, физические оси — в пресет не входит);
любое другое состояние — `USER`, нетронутые настройки — `NONE`.

Список параметров стиков, эффектов кнопок и пресетов — в английской части выше (названия параметров и эффектов в приложении
английские). Коротко:

- **Стики:** 61 параметр — GRAIN и GRAIN 2/3, roam, FX и TAPE, ORBIX, **ORBIX Rings**, **OSCILLATOR**, темп, уровни LIVE/мастера.
- **Эффекты кнопок:** 29, из них новые — Scatter, Reverse Grains, Rings Bloom/Damp/Detune, Osc On/Drive/FM, Slow Down/Speed Up,
  Tempo +5/−5, Input Cut/Boost, Mute Out. Hold-эффекты возвращают значения, бывшие до нажатия; шаговые (Octave ±, Tempo ±5) меняют значение насовсем.
- **Пресеты:** Granular, Ambient, Texture, Echo, Tape, ORBIX Play, **Rhythm, Rings, Oscillator, Live, Grain 2/3** и слот User.
- **Хранение:** `settings.json` → `grainbernik_advanced`; неизвестные параметры загружаются как *None*, остальной `settings.json` сохраняется.
- **Где работает:** GRAIN, FX, TAPE, VISUAL; не работает при открытых INFO, переназначении кнопок, странице Bluetooth MIDI и вводе имени проекта.
  L3/R3 перехватываются на всех экранах, пока включены; L2/R2 — только на звуковых вкладках и только при назначенном эффекте.
- **Отключить страницу:** `GRAINBERNIK_ADVANCED=0` в `GrainBrick BETA 2.0.sh`.
