#!/bin/sh
# GrainBernik: assemble the ROCKNIX installation package.
#   sh rocknix/make_package.sh /path/to/grainbrick.beta.1.0.1.zip [output_dir]
#   sh rocknix/make_package.sh /path/to/GrainBrick_BETA_2_0.zip   [output_dir]
# Result (default: ./grainbernik-rocknix): official GrainBrick app +
# GrainBernik patch + ROCKNIX launcher + USB audio modules + install.sh.
# The official GrainBrick app is taken from YOUR copy of the official ZIP;
# the version (1.0.1 or BETA 2.0) is detected from the folder inside it.
set -eu
ZIP=${1:?usage: make_package.sh grainbrick.beta.1.0.1.zip [output_dir]}
OUT=${2:-grainbernik-rocknix}
HERE=$(cd "$(dirname "$0")" && pwd)
REPO=$(dirname "$HERE")
APP=$(python3 - "$ZIP" "$OUT" <<'PY'
import sys, zipfile
zip_path, out = sys.argv[1:3]
with zipfile.ZipFile(zip_path) as z:
    names = z.namelist()
    for app in ('grainbrick-beta2', 'grainbrick beta 1.0.1'):
        members = [n for n in names if n.startswith(app + '/')]
        if members:
            break
    else:
        raise SystemExit('not an official GrainBrick ZIP: no "grainbrick-beta2/" or "grainbrick beta 1.0.1/" folder')
    if app == 'grainbrick-beta2' and 'grainbrick-beta2/main.py' not in names:
        raise SystemExit('BETA 2.0 ZIP has no grainbrick-beta2/main.py')
    z.extractall(out, members)
    print(app)
PY
)
case "$APP" in
  grainbrick-beta2)
    PATCH="$REPO/rg40xx-h-patch/grainbrick-beta2"
    LAUNCHER='GrainBrick BETA 2.0.sh'
    cp "$PATCH/"*.py "$OUT/$APP/"
    # Adapters shared with the 1.0.1 patch and verified against BETA 2.0.
    cp "$REPO/rg40xx-h-patch/grainbrick-beta/gb_shutdown.py" "$OUT/$APP/"
    ;;
  *)
    LAUNCHER='GrainBrick beta 1.0.1.sh'
    cp "$REPO/rg40xx-h-patch/grainbrick-beta/"*.py "$REPO/rg40xx-h-patch/grainbrick-beta/"*.sh "$OUT/$APP/"
    ;;
esac
cp "$HERE/$LAUNCHER" "$HERE/install.sh" "$HERE/gb-diag.sh" "$OUT/"
mkdir -p "$OUT/wireplumber"
cp "$HERE/wireplumber/99-grainbrick-driver.conf" "$OUT/wireplumber/"
mkdir -p "$OUT/uac2"
cp "$HERE/uac2/"* "$OUT/uac2/"
echo "Package ready: $OUT"
echo "Copy to the console:  scp -r \"$OUT\" root@<console-ip>:/storage/"
echo "Install on the console: sh /storage/$(basename "$OUT")/install.sh"
