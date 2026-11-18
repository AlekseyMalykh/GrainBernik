#!/bin/sh
# GrainBernik installer for ROCKNIX (RG40XX H). Run on the console:
#   sh /storage/grainbernik-rocknix/install.sh
# Needs Wi-Fi with internet once (downloads Python 3.12 and pygame, checks SHA-256).
set -eu
HERE=$(cd "$(dirname "$0")" && pwd)
PY=/storage/grainbrick-python
PORTS=/storage/roms/ports
# Which official GrainBrick is in this package: BETA 2.0 or 1.0.1.
if [ -d "$HERE/grainbrick-beta2" ]; then
  APPN='grainbrick-beta2'; LAUNCHER='GrainBrick BETA 2.0.sh'
else
  APPN='grainbrick beta 1.0.1'; LAUNCHER='GrainBrick beta 1.0.1.sh'
fi
TMP=/storage/.gb-install
PYURL='https://github.com/astral-sh/python-build-standalone/releases/download/20261026/cpython-3.12.16%2B20261026-aarch64-unknown-linux-gnu-install_only.tar.gz'
PYSHA=a945427411dc6851a1393533b74a4a1ac434321ae397f2ec69897a9b4fde032b
PGURL='https://files.pythonhosted.org/packages/06/be/3ed337583f010696c3b3435e89a74fb29d0c74d0931e8f33c0a4246307a9/pygame-2.6.1-cp312-cp312-manylinux_2_17_aarch64.manylinux2014_aarch64.whl'
PGSHA=c47a6938de93fa610accd4969e638c2aebcb29b2fca518a84c3a39d91ab47116
mkdir -p "$TMP" "$PORTS"

echo "=== 1/4 Python 3.12"
if [ ! -x "$PY/bin/python3.12" ]; then
  [ -f "$TMP/py.tgz" ] || curl -fL -o "$TMP/py.tgz" "$PYURL"
  echo "$PYSHA  $TMP/py.tgz" | sha256sum -c -
  rm -rf "$TMP/py"; mkdir -p "$TMP/py"; tar xzf "$TMP/py.tgz" -C "$TMP/py"
  rm -rf "$PY"; mv "$TMP/py/python" "$PY"
fi
"$PY/bin/python3.12" -c 'import sys; print(sys.version)'

echo "=== 2/4 pygame 2.6.1"
if [ ! -d "$PY/site/pygame" ]; then
  [ -f "$TMP/pygame.whl" ] || curl -fL -o "$TMP/pygame.whl" "$PGURL"
  echo "$PGSHA  $TMP/pygame.whl" | sha256sum -c -
  mkdir -p "$PY/site"; "$PY/bin/python3.12" -m zipfile -e "$TMP/pygame.whl" "$PY/site"
fi
# Use ROCKNIX's own SDL2 (built for its Wayland/sway session) instead of the bundled one.
SYS=/usr/lib/libSDL2-2.0.so.0
if [ -e "$SYS" ]; then
  for f in "$PY"/site/pygame.libs/libSDL2-*; do
    case "$f" in *.bundled) continue;; esac
    if [ -f "$f" ] && [ ! -L "$f" ]; then mv "$f" "$f.bundled"; ln -s "$SYS" "$f"; echo "SDL2 -> $SYS"; fi
  done
fi
PYTHONPATH="$PY/site" "$PY/bin/python3.12" -c 'import os; os.environ["PYGAME_HIDE_SUPPORT_PROMPT"]="1"; import pygame; print("pygame", pygame.version.ver, "SDL", pygame.get_sdl_version())'

echo "=== 3/4 GrainBrick + GrainBernik patch"
mkdir -p "$PORTS/$APPN"
# BETA 2.0 ships its own settings, demo projects and samples: keep the user's
# own data when re-installing over an existing copy (restored after the copy).
KEEP='samples projects recordings orbix_presets settings.json tempo_settings.json sample_meta.json harmony_samples.json button_mapping.json midi_learn.json midi_settings.json ble_midi_devices.json gb_usb_audio.json sound_state.json rhythm_state.json orbix_resonator_state.json'
KEPT="$TMP/userdata"
rm -rf "$KEPT"
if [ "$APPN" = grainbrick-beta2 ] && [ -f "$PORTS/$APPN/main.py" ]; then
  mkdir -p "$KEPT"
  for f in $KEEP; do
    [ -e "$PORTS/$APPN/$f" ] && cp -a "$PORTS/$APPN/$f" "$KEPT/" && echo "kept: $f"
  done
fi
cp -a "$HERE/$APPN/." "$PORTS/$APPN/"
# Carry the iPhone / USB audio settings over from a GrainBernik 1.0.1 install.
OLD101="$PORTS/grainbrick beta 1.0.1/gb_usb_audio.json"
if [ "$APPN" = grainbrick-beta2 ] && [ -f "$OLD101" ] && [ ! -e "$KEPT/gb_usb_audio.json" ] \
   && [ ! -e "$PORTS/$APPN/gb_usb_audio.json" ]; then
  cp "$OLD101" "$PORTS/$APPN/gb_usb_audio.json" && echo "migrated: gb_usb_audio.json from 1.0.1"
fi
if [ -d "$KEPT" ]; then
  for f in $KEEP; do
    if [ -e "$KEPT/$f" ]; then
      rm -rf "$PORTS/$APPN/$f"
      cp -a "$KEPT/$f" "$PORTS/$APPN/$f"
    fi
  done
  rm -rf "$KEPT"
fi
cp "$HERE/$LAUNCHER" "$PORTS/"
chmod +x "$PORTS/$LAUNCHER" "$PORTS/$APPN"/*.sh 2>/dev/null || true

echo "=== USB Audio (UAC2) modules and scripts -> /storage/uac2"
mkdir -p /storage/uac2
cp "$HERE"/uac2/* /storage/uac2/
chmod +x /storage/uac2/*.sh

echo "=== PipeWire: remove the old rule that hid the USB Audio card"
rm -f /storage/.config/wireplumber/wireplumber.conf.d/90-grainbernik-uac2.conf /run/udev/rules.d/90-grainbernik-uac2.rules
echo "=== PipeWire: pin internal H616 speaker as the audio graph driver"
WP_DIR=/storage/.config/wireplumber/wireplumber.conf.d
mkdir -p "$WP_DIR"
cp "$HERE/wireplumber/99-grainbrick-driver.conf" "$WP_DIR/99-grainbrick-driver.conf"
systemctl restart wireplumber 2>/dev/null || true

echo "=== 4/4 Import check (without opening the window)"
cd "$PORTS/$APPN"
PYTHONPATH="$PY/site:$PORTS/$APPN/_vendor" LD_LIBRARY_PATH="$PORTS/$APPN" "$PY/bin/python3.12" -c 'import numpy; print("numpy", numpy.__version__)'
echo
echo "Готово. Перезапустите меню (Start > Quit > Restart EmulationStation) или выполните: systemctl restart essway"
echo "GrainBrick появится в разделе PORTS. Журнал запуска: $PORTS/$APPN/gb_launch.log"
