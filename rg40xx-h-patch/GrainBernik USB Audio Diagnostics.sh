#!/bin/sh
BASE=/userdata/roms/ports
if [ -d "$BASE/grainbrick beta 1.0.1" ]; then
  APP="$BASE/grainbrick beta 1.0.1"
else
  APP="$BASE/grainbrick-beta"
fi
# Only writes the requested report beside the app, never system configuration.
exec python3 -B "$APP/gb_usb_gadget.py" --commands > "$APP/usb_audio_diag.json" 2>&1
