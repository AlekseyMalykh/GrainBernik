#!/bin/sh
APP='/storage/roms/ports/grainbrick beta 1.0.1'
cd "$APP" || exit 1
/usr/bin/python3 -B gb_usb_gadget.py --commands > "$APP/usb_audio_diag.json" 2> "$APP/usb_audio_diag.log"
