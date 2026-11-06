#!/bin/sh
# GrainBernik diagnostics for ROCKNIX (read-only).
A='/storage/roms/ports/grainbrick beta 1.0.1'
s() { printf '\n##### %s\n' "$*"; }
s launch log; tail -n 120 "$A/gb_launch.log"
s gb_buttons.json; cat "$A/gb_buttons.json" 2>&1
s app files; ls -la "$A" | grep -v -E '\.so|demo|THIRD'
s settings json; for f in "$A"/*.json; do case "$f" in *SHA256*|*gb_buttons*) continue;; esac; echo "== $f"; head -c 4000 "$f"; echo; done
s env; . /etc/profile >/dev/null 2>&1; env | grep -E '^(SDL|WAYLAND|XDG|HOTKEY|DEVICE|QUIRK|UI_SERVICE)' | sort
s gamecontrollerdb; grep -h "H700" "$SDL_GAMECONTROLLERCONFIG_FILE" /usr/config/SDL-GameControllerDB/gamecontrollerdb.txt 2>/dev/null | head -3
s cpu; for p in /sys/devices/system/cpu/cpufreq/policy*; do echo "$p $(cat $p/scaling_governor) $(cat $p/scaling_cur_freq) max=$(cat $p/scaling_max_freq)"; done; uptime
s display; cat /sys/class/drm/*/modes 2>/dev/null | head; swaymsg -t get_outputs 2>/dev/null | grep -E '"name"|current_mode|width|height|scale|refresh' | head -20
s processes; ps | grep -v -E '\[|ps$|grep' | head -60
s usb gadget; cat /sys/class/udc/*/state; for g in /sys/kernel/config/usb_gadget/*/; do echo "$g UDC=$(cat $g/UDC 2>/dev/null)"; ls $g/functions; done; grep -E 'u_audio|uac2' /proc/modules
s sound cards; cat /proc/asound/cards; for f in /proc/asound/card1/pcm0*/sub0/status; do echo "== $f"; cat $f; done
s dmesg; dmesg | grep -iE 'musb|udc|gadget|uac|audio|usb' | tail -n 40
