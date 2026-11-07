#!/bin/sh
# GrainBernik: assemble the ROCKNIX installation package.
#   sh rocknix/make_package.sh /path/to/grainbrick.beta.1.0.1.zip [output_dir]
# Result (default: ./grainbernik-rocknix): official GrainBrick 1.0.1 app +
# GrainBernik patch + ROCKNIX launcher + USB audio modules + install.sh.
# The closed GrainBrick app is taken from YOUR copy of the official ZIP.
set -eu
ZIP=${1:?usage: make_package.sh grainbrick.beta.1.0.1.zip [output_dir]}
OUT=${2:-grainbernik-rocknix}
HERE=$(cd "$(dirname "$0")" && pwd)
REPO=$(dirname "$HERE")
APP='grainbrick beta 1.0.1'
mkdir -p "$OUT"
python3 - "$ZIP" "$OUT" "$APP" <<'PY'
import sys, zipfile
zip_path, out, app = sys.argv[1:4]
with zipfile.ZipFile(zip_path) as z:
    members = [n for n in z.namelist() if n.startswith(app + '/')]
    if not members:
        raise SystemExit('not the official GrainBrick 1.0.1 ZIP: no "%s/" folder' % app)
    z.extractall(out, members)
PY
cp "$REPO/rg40xx-h-patch/grainbrick-beta/"*.py "$REPO/rg40xx-h-patch/grainbrick-beta/"*.sh "$OUT/$APP/"
cp "$HERE/GrainBrick beta 1.0.1.sh" "$HERE/install.sh" "$HERE/gb-diag.sh" "$OUT/"
mkdir -p "$OUT/wireplumber"
cp "$HERE/wireplumber/99-grainbrick-driver.conf" "$OUT/wireplumber/"
mkdir -p "$OUT/uac2"
cp "$HERE/uac2/"* "$OUT/uac2/"
echo "Package ready: $OUT"
echo "Copy to the console:  scp -r \"$OUT\" root@<console-ip>:/storage/"
echo "Install on the console: sh /storage/$(basename "$OUT")/install.sh"
