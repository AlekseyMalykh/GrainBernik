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

# Screen adapter (RG40XX H 640x480 etc.).
_fit_path = APP / 'gb_display_fit.py'
if _fit_path.is_file():
    try:
        _spec = importlib.util.spec_from_file_location('gb_display_fit', _fit_path)
        _fit = importlib.util.module_from_spec(_spec)
        _spec.loader.exec_module(_fit)
        _fit.install()
    except Exception as exc:
        print('GB DISPLAY FIT FAILED:', repr(exc), flush=True)

os.environ['GRAINBRICK_ROOT'] = str(APP)
sys.path.insert(0,str(APP))
importlib.import_module('main')
