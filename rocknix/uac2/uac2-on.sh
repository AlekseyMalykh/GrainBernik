#!/bin/sh
# GrainBernik: включить USB Audio (UAC2, stereo 16-bit 48 kHz в обе стороны) на ROCKNIX.
# Запускать по SSH через Wi-Fi (не через USB-сеть: она отключится).
# Ничего не пишет в систему; после перезагрузки всё как было. Выключить: uac2-off.sh
set -e
D=$(cd "$(dirname "$0")" && pwd)
CFG=/sys/kernel/config/usb_gadget
G=$CFG/grainbernik
UDC=$(ls /sys/class/udc | head -1)
[ -n "$UDC" ] || { echo "Нет USB-контроллера в режиме устройства"; exit 1; }

grep -q '^u_audio ' /proc/modules || insmod "$D/u_audio.ko"
grep -q '^usb_f_uac2 ' /proc/modules || insmod "$D/usb_f_uac2.ko"

# Освободить контроллер от других gadget (запоминаем, чтобы вернуть)
for g in "$CFG"/*/; do
  n=$(basename "$g"); [ "$n" = grainbernik ] && continue
  if [ "$(cat "$g/UDC" 2>/dev/null)" = "$UDC" ]; then
    echo "$n" > /run/gb-uac2-prev; echo "" > "$g/UDC"; echo "Отключён gadget: $n"
  fi
done

if [ ! -d "$G" ]; then
  mkdir "$G"
  echo 0x1d6b > "$G/idVendor"; echo 0x0104 > "$G/idProduct"
  echo 0x0100 > "$G/bcdDevice"; echo 0x0200 > "$G/bcdUSB"
  mkdir -p "$G/strings/0x409"
  echo "Anbernic" > "$G/strings/0x409/manufacturer"
  echo "GrainBernik" > "$G/strings/0x409/product"
  echo "GB0001" > "$G/strings/0x409/serialnumber"
  mkdir -p "$G/configs/c.1/strings/0x409"
  echo "Audio" > "$G/configs/c.1/strings/0x409/configuration"
  F="$G/functions/uac2.gb"; mkdir "$F"
  for a in p c; do
    echo 3 > "$F/${a}_chmask"; echo 48000 > "$F/${a}_srate"; echo 2 > "$F/${a}_ssize"
  done
  [ -e "$F/function_name" ] && echo "GrainBernik" > "$F/function_name"
  ln -s "$F" "$G/configs/c.1/"
fi

# Self-powered, minimal bus current: iOS refuses bus-powered accessories
# that announce or draw too much ("accessory uses too much power").
echo "" > "$G/UDC" 2>/dev/null || true
echo 0xC0 > "$G/configs/c.1/bmAttributes" || echo "warning: bmAttributes not set"
echo 2 > "$G/configs/c.1/MaxPower" || echo "warning: MaxPower not set"

# Do not charge from the USB host (iPhone) while in audio mode: keep the
# charger's USB input current at its minimum. uac2-off.sh restores it.
if [ ! -f /run/gb-uac2-ilim ]; then
  for ps in /sys/class/power_supply/*; do
    [ "$(cat "$ps/type" 2>/dev/null)" = USB ] && [ -w "$ps/input_current_limit" ] || continue
    echo "$ps $(cat "$ps/input_current_limit")" >> /run/gb-uac2-ilim
    echo 100000 > "$ps/input_current_limit" 2>/dev/null && echo "USB input current limit: $ps -> 100 mA"
  done
fi

echo "$UDC" > "$G/UDC"
sleep 1
echo "--- dmesg:"; dmesg | tail -n 12
echo "--- звуковые карты:"; cat /proc/asound/cards
echo "--- состояние USB: $(cat /sys/class/udc/$UDC/state 2>/dev/null)"
