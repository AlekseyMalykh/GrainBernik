#!/bin/sh
set -u
APP='/storage/roms/ports/grainbrick beta 1.0.1'
RUNTIME=/usr/lib/grainbrick-python
cd "$APP" || exit 1
mkdir -p samples projects recordings || exit 1
export GRAINBRICK_ROOT="$APP"
export GRAINBRICK_DISPLAY_FILTER=smooth
export PYTHONUNBUFFERED=1
export PYTHONHOME="$RUNTIME"
export PYTHONPATH="$APP/_vendor:$RUNTIME/site:$APP"
export LD_LIBRARY_PATH="$APP:$RUNTIME/lib/aarch64-linux-gnu${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
printf '\n=== GrainBrick on ROCKNIX USB Audio test image ===\n' >> gb_launch.log
"$RUNTIME/bin/python3.12" -B gb_launch.py >> gb_launch.log 2>&1
result=$?
printf 'GrainBrick exit: %s\n' "$result" >> gb_launch.log
exit "$result"
