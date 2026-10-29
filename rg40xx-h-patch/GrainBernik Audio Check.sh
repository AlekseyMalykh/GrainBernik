#!/bin/sh
# GrainBernik: collect USB audio diagnostics into grainbrick-beta/audio_check.txt
OUT=/userdata/roms/ports/grainbrick-beta/audio_check.txt
{
  echo "=== date"; date
  echo "=== uname"; uname -a
  echo "=== /proc/asound/cards"; cat /proc/asound/cards
  echo "=== /proc/asound/pcm"; cat /proc/asound/pcm
  for d in /proc/asound/card*; do
    echo "--- $d"; ls "$d"; [ -f "$d/usbid" ] && echo "usbid: $(cat "$d/usbid")"
    [ -f "$d/stream0" ] && cat "$d/stream0"
  done
  echo "=== aplay -l"; aplay -l 2>&1
  echo "=== arecord -l"; arecord -l 2>&1
  echo "=== lsusb"; lsusb 2>&1
  echo "=== /sys/bus/usb/devices"
  for d in /sys/bus/usb/devices/*; do
    [ -f "$d/idVendor" ] && echo "$(basename "$d") $(cat "$d/idVendor"):$(cat "$d/idProduct") $(cat "$d/manufacturer" 2>/dev/null) $(cat "$d/product" 2>/dev/null) power=$(cat "$d/bMaxPower" 2>/dev/null)"
  done
  echo "=== usb role / otg"
  for f in /sys/class/usb_role/*/role /sys/devices/platform/*usb*/*/mode /sys/devices/platform/soc*/*usb*/*/mode; do
    [ -f "$f" ] && echo "$f: $(cat "$f")"
  done
  echo "=== modules (snd/usb)"; lsmod 2>/dev/null | grep -iE 'snd|usb|audio'
  echo "=== snd-usb-audio module file"; find /lib/modules -iname '*snd-usb*' 2>/dev/null
  echo "=== config"; zcat /proc/config.gz 2>/dev/null | grep -E 'CONFIG_SND_USB|CONFIG_USB_OTG|CONFIG_USB_MUSB|CONFIG_USB_EHCI|CONFIG_USB_OHCI|CONFIG_USB_XHCI'
  echo "=== dmesg (usb/audio)"; dmesg 2>/dev/null | grep -iE 'usb|audio|snd' | tail -n 80
} > "$OUT" 2>&1
sync
