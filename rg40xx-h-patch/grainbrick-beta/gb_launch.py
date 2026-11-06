# Public bootstrap for GrainBrick beta 1.0 / 1.0.1. No proprietary source.
# GrainBrick 1.0.1 bundles NumPy and has native resolution and USB-audio
# handling. Legacy adapters remain available for beta 1.0 installations.
import importlib
import importlib.util
import os
from pathlib import Path
import platform
import sys

APP = Path(__file__).resolve().parent
if sys.version_info[:2] != (3, 12):
    raise SystemExit('GrainBrick: KNULLI Python 3.12 required')
if platform.machine().lower() not in ('aarch64', 'arm64'):
    raise SystemExit('GrainBrick: ARM64 required')

# Do not let an app-local directory shadow KNULLI's Pygame. The 1.0.1
# distribution intentionally bundles NumPy in _vendor; beta 1.0 uses the
# system installation (or the optional user-provided compatibility package).
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
if vendor.is_dir() and (vendor not in Path(numpy.__file__).resolve().parents or numpy.__version__ != '1.26.4'):
    raise SystemExit('GrainBrick: incompatible bundled NumPy: ' + str(numpy.__file__))
print('EXTERNAL PYGAME:', pygame.__file__, 'NUMPY:', numpy.__file__, flush=True)

IS_UNIVERSAL_101 = vendor.is_dir()

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

# These adapters address hardware behavior that remains useful on the H.
_load_adapter('gb_shutdown')
_load_adapter('gb_recording')
_load_adapter('gb_buttons')
_load_adapter('gb_advanced')

# Optional gadget routing/settings; default Disabled, no ConfigFS writes.
# Its imports use sibling modules and must also work before main is loaded.
sys.path.insert(0, str(APP))
_load_adapter('gb_usb_settings')
_load_adapter('gb_samples')
_load_adapter('gb_quick_settings')
sys.path.remove(str(APP))

# 1.0.1 now detects display sizes and USB capture devices itself. Keep its
# native implementations by default; allow the older adapters as opt-ins.
if not IS_UNIVERSAL_101 or os.environ.get('GRAINBERNIK_FIT', '0') == '1':
    _load_adapter('gb_display_fit')
if not IS_UNIVERSAL_101 or os.environ.get('GRAINBERNIK_LEGACY_AUDIO', '0') == '1':
    _load_adapter('gb_audio')

os.environ['GRAINBRICK_ROOT'] = str(APP)
sys.path.insert(0, str(APP))
importlib.import_module('main')
