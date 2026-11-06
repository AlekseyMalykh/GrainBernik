#!/bin/sh
# Read-only. stdout only; redirect to a file if desired. No module loading,
# ConfigFS mounting, role changes, PCM opens or power-setting writes.
HERE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd) || exit 1
exec python3 -B "$HERE/gb_usb_gadget.py" --commands "$@"
