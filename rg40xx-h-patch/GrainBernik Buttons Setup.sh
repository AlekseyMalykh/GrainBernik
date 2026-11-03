#!/bin/sh
# GrainBernik: (re)record the RG40XX H button layout for GrainBrick.
BASE=/userdata/roms/ports
if [ -d "$BASE/grainbrick beta 1.0.1" ]; then
  BETA_DIR="$BASE/grainbrick beta 1.0.1"
else
  BETA_DIR="$BASE/grainbrick-beta"
fi
cd "$BETA_DIR" || exit 1
if [ ! -d "$BETA_DIR/_vendor/numpy" ]; then
  export PYTHONPATH="/userdata/system/grainbrick-deps${PYTHONPATH:+:$PYTHONPATH}"
fi
printf '\n=== GrainBernik button setup ===\n' >> "$BETA_DIR/gb_launch.log"
python3 -B "$BETA_DIR/gb_buttons.py" calibrate >> "$BETA_DIR/gb_launch.log" 2>&1
