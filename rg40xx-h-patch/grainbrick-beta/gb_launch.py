# Public bootstrap, deliberately contains no proprietary application source.
# + RG40XX H patch: scales the Brick 1024x768 UI to the real screen.
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

# Import official KNULLI pygame/numpy before adding this app directory, so
# an old standalone release's leftover folders cannot shadow system packages.
sys.path[:] = [p for p in sys.path if Path(p or os.getcwd()).resolve() != APP]
import pygame
import numpy
for package in (pygame, numpy):
    location = Path(package.__file__).resolve()
    if APP == location or APP in location.parents:
        raise SystemExit('GrainBrick: embedded third-party package detected: ' + str(location))
print('EXTERNAL PYGAME:',pygame.__file__, 'NUMPY:',numpy.__file__,flush=True)

# GrainBernik adapters for RG40XX H: button layout first (may show the
# one-time calibration screen), then screen scaling 1024x768 -> 640x480.
def _load_adapter(name):
    path = APP / (name + '.py')
    if not path.is_file():
        return
    try:
        spec = importlib.util.spec_from_file_location(name, path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        mod.install()
    except Exception as exc:
        print('GRAINBERNIK ADAPTER FAILED:', name, repr(exc), flush=True)

_load_adapter('gb_buttons')
_load_adapter('gb_display_fit')

os.environ['GRAINBRICK_ROOT'] = str(APP)
sys.path.insert(0,str(APP))
importlib.import_module('main')
