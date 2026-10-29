#!/bin/sh
# GrainBernik: (re)record the RG40XX H button layout for GrainBrick.
BETA_DIR=/userdata/roms/ports/grainbrick-beta
cd "$BETA_DIR" || exit 1
export PYTHONPATH="/userdata/system/grainbrick-deps${PYTHONPATH:+:$PYTHONPATH}"
printf '\n=== GrainBernik button setup ===\n' >> "$BETA_DIR/beta_port_launcher.log"
python3 -B "$BETA_DIR/gb_buttons.py" calibrate >> "$BETA_DIR/beta_port_launcher.log" 2>&1
