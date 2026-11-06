#!/bin/sh
# GrainBernik: выключить USB Audio и вернуть прежний USB-режим ROCKNIX (сеть по USB).
CFG=/sys/kernel/config/usb_gadget
UDC=$(ls /sys/class/udc | head -1)
[ -d "$CFG/grainbernik" ] && echo "" > "$CFG/grainbernik/UDC" 2>/dev/null
prev=$(cat /run/gb-uac2-prev 2>/dev/null)
if [ -n "$prev" ] && [ -d "$CFG/$prev" ]; then
  echo "$UDC" > "$CFG/$prev/UDC" && echo "Возвращён gadget: $prev"
fi
if [ -f /run/gb-uac2-ilim ]; then
  while read -r ps value; do echo "$value" > "$ps/input_current_limit" 2>/dev/null; done < /run/gb-uac2-ilim
  rm -f /run/gb-uac2-ilim
fi
echo "USB Audio выключен"
