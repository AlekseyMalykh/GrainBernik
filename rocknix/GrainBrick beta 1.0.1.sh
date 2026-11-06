#!/bin/sh
# GrainBernik (GrainBrick 1.0.1 + RG40XX H patch) for ROCKNIX.
# Uses a separate Python 3.12 + pygame in /storage/grainbrick-python.
. /etc/profile 2>/dev/null
set -u
APP='/storage/roms/ports/grainbrick beta 1.0.1'
PY=/storage/grainbrick-python
LOG="$APP/gb_launch.log"
cd "$APP" || exit 1
mkdir -p "$APP/samples" "$APP/projects" "$APP/recordings" || exit 1
for wav in "$APP"/demo-samples/*.wav; do
  [ -f "$wav" ] || continue
  name=${wav##*/}
  [ -e "$APP/samples/$name" ] || cp "$wav" "$APP/samples/$name"
done
[ -e "$APP/projects/AMBIENT.json" ] || cp "$APP/demo-projects/AMBIENT.json" "$APP/projects/AMBIENT.json" 2>/dev/null
export GRAINBRICK_ROOT="$APP"
export GRAINBRICK_DISPLAY_FILTER=smooth
export PYTHONUNBUFFERED=1
export PYTHONPATH="$PY/site"
export LD_LIBRARY_PATH="$APP${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export SDL_VIDEODRIVER="${SDL_VIDEODRIVER:-wayland}"
# GrainBrick 1.0.1 maps buttons itself through the SDL controller mapping.
# The old KNULLI calibration layer (gb_buttons) would translate twice: keep it off.
export GRAINBRICK_BUTTONS="${GRAINBRICK_BUTTONS:-0}"
JS=$(cat /sys/class/input/js0/device/name 2>/dev/null)
if [ -z "${SDL_GAMECONTROLLERCONFIG:-}" ] && [ -n "$JS" ] && [ -f "${SDL_GAMECONTROLLERCONFIG_FILE:-}" ]; then
  MAP="$(grep -F ",$JS," "$SDL_GAMECONTROLLERCONFIG_FILE" | head -n 1)"
  # ROCKNIX names face buttons by their printed label (a = button marked A),
  # GrainBrick 1.0.1 expects positional SDL names like KNULLI (a = bottom).
  if [ "${GRAINBERNIK_SWAP_ABXY:-1}" = 1 ]; then
    MAP="$(printf '%s' "$MAP" | sed -e 's/,a:/,@A:/; s/,b:/,a:/; s/,@A:/,b:/' -e 's/,x:/,@X:/; s/,y:/,x:/; s/,@X:/,y:/')"
  fi
  export SDL_GAMECONTROLLERCONFIG="$MAP"
fi
# Full CPU speed while GrainBrick runs (restored on exit).
GOV=/sys/devices/system/cpu/cpufreq/policy0/scaling_governor
OLD_GOV=$(cat "$GOV" 2>/dev/null)
[ -w "$GOV" ] && echo performance > "$GOV"
printf '\n=== GrainBernik on ROCKNIX %s ===\n' "$(date)" >> "$LOG"
env | grep -E '^(SDL_|WAYLAND|XDG_RUNTIME|GRAINBRICK_BUTTONS|GRAINBERNIK)' >> "$LOG"
"$PY/bin/python3.12" -B "$APP/gb_launch.py" >> "$LOG" 2>&1
result=$?
[ -n "$OLD_GOV" ] && [ -w "$GOV" ] && echo "$OLD_GOV" > "$GOV"
printf 'GrainBrick exit: %s\n' "$result" >> "$LOG"
exit "$result"
