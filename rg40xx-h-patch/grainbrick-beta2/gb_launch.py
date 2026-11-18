# GrainBernik bootstrap for the official GrainBrick BETA 2.0 (ROCKNIX, RG40XX H).
# No proprietary source is included: this file only prepares the environment,
# loads the optional GrainBernik adapters, and imports the official main.py.
#
# Beta 2.0 port: only adapters that are verified against the Beta 2.0 sources
# are loaded (see docs/BETA2_PORT.md):
#   gb_shutdown     - recovers a stalled audio worker on Select+Start exit.
#   gb_usb_settings - IPHONE / USB AUDIO page and PipeWire routing (step 2).
# Beta 2.0 already repairs recording WAV headers itself and has the same SDL
# controller / display / USB-capture handling as 1.0.1, so gb_recording,
# gb_buttons, gb_display_fit and gb_audio are intentionally NOT loaded.
# The Advanced Settings, quick settings and sample adapters are not ported
# yet and are not loaded either.
import importlib
import importlib.util
import os
from pathlib import Path
import platform
import sys

APP = Path(__file__).resolve().parent
if sys.version_info[:2] != (3, 12):
    raise SystemExit('GrainBrick: Python 3.12 required')
if platform.machine().lower() not in ('aarch64', 'arm64'):
    raise SystemExit('GrainBrick: ARM64 required')
if not (APP / 'main.py').is_file():
    raise SystemExit('GrainBrick: official BETA 2.0 main.py not found in ' + str(APP))

# Do not let the app folder shadow the system pygame; Beta 2.0 bundles NumPy
# in _vendor and expects exactly that copy.
sys.path[:] = [p for p in sys.path if Path(p or os.getcwd()).resolve() != APP]
vendor = APP / '_vendor'
if vendor.is_dir():
    sys.path.insert(0, str(vendor))
try:
    import pygame
    import numpy
except Exception as exc:
    raise SystemExit('GrainBrick: dependency load failed: ' + repr(exc)) from exc

for package in (pygame, numpy):
    location = Path(package.__file__).resolve()
    if APP == location or APP in location.parents and vendor not in location.parents:
        raise SystemExit('GrainBrick: unexpected app-local dependency: ' + str(location))
if vendor.is_dir() and (vendor not in Path(numpy.__file__).resolve().parents
                        or numpy.__version__ != '1.26.4'):
    raise SystemExit('GrainBrick: incompatible bundled NumPy: ' + str(numpy.__file__))
print('EXTERNAL PYGAME:', pygame.__file__, 'NUMPY:', numpy.__file__, flush=True)


def _load_adapter(name):
    path = APP / (name + '.py')
    if not path.is_file():
        return
    try:
        spec = importlib.util.spec_from_file_location(name, path)
        mod = importlib.util.module_from_spec(spec)
        sys.modules[name] = mod
        spec.loader.exec_module(mod)
        mod.install()
    except Exception as exc:
        print('GRAINBERNIK ADAPTER FAILED:', name, repr(exc), flush=True)


_load_adapter('gb_shutdown')

# Optional iPhone / USB audio page; default OFF, no ConfigFS writes until the
# user selects the IPHONE mode. Its imports use sibling modules.
sys.path.insert(0, str(APP))
_load_adapter('gb_usb_settings')
sys.path.remove(str(APP))

os.environ['GRAINBRICK_ROOT'] = str(APP)
sys.path.insert(0, str(APP))
importlib.import_module('main')
