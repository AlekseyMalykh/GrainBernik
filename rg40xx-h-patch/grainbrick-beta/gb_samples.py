"""Delete recorded samples from GrainBrick's SAMPLE browser (1.0.1).

SELECT on a recording in samples/recordings arms deletion, a second SELECT
within a few seconds deletes the file. Only WAV files inside the recordings
folder can be deleted; demo samples and other folders are never touched. On
any other row SELECT keeps its native function (info window).
The sample currently loaded (playing) in GrainBrick is protected.
Disable: GRAINBERNIK_SAMPLE_DELETE=0
"""
import os
from pathlib import Path
import sys
import time

import pygame

CONFIRM_SECONDS = 4.0
_state = dict(browser=None, index=None, entry=None, visible_until=0.0, armed=None,
              armed_at=0.0, message='', message_until=0.0, controller=None, dumped=False,
              loaded=None)


def _log(message):
    print('GB SAMPLES: ' + message, flush=True)


def _recordings_dir():
    main = sys.modules.get('main')
    path = getattr(main, 'RECORDINGS_SAMPLE_DIR', None)
    if path:
        return Path(path)
    return Path(__file__).resolve().parent / 'samples' / 'recordings'


def _entry_path(browser, entry):
    if entry is None:
        return None
    attrs = {}
    try:
        attrs = dict(vars(entry))
    except TypeError:
        for name in ('path', 'name', 'full_path', 'filename', 'is_dir'):
            if hasattr(entry, name):
                attrs[name] = getattr(entry, name)
    if not _state['dumped']:
        _state['dumped'] = True
        _log('entry attributes: %r' % {k: (v if isinstance(v, (str, int, float, bool)) or v is None else str(v))
                                         for k, v in attrs.items()})
    for key in ('path', 'full_path', 'filepath', 'file', 'abs_path'):
        value = attrs.get(key)
        if isinstance(value, (str, Path)) and os.path.isabs(str(value)):
            return Path(value)
    name = attrs.get('name') or attrs.get('filename')
    if isinstance(name, str):
        for key in ('current', 'current_dir', 'cwd', 'directory', 'path', 'dir'):
            base = getattr(browser, key, None)
            if isinstance(base, (str, Path)) and os.path.isdir(str(base)):
                return Path(base) / name
        root = getattr(browser, 'root', None)
        rel = getattr(browser, 'relative_dir', None)
        if isinstance(root, (str, Path)) and isinstance(rel, str):
            return Path(root) / rel.strip('/') / name
    for value in attrs.values():
        if isinstance(value, (str, Path)) and os.path.isfile(str(value)):
            return Path(value)
    return None


def deletable(path):
    if path is None:
        return False
    try:
        real = Path(os.path.realpath(path))
        folder = Path(os.path.realpath(_recordings_dir()))
    except OSError:
        return False
    return real.is_file() and real.suffix.lower() == '.wav' and folder in real.parents


def _sample_path(sample):
    """Best effort: file path of the SampleBuffer GrainBrick has loaded."""
    if sample is None:
        return None
    for key in ('path', 'file_path', 'filepath', 'source_path', 'filename', 'source'):
        value = getattr(sample, key, None)
        if isinstance(value, (str, Path)) and os.path.isabs(str(value)):
            return str(Path(os.path.realpath(value)))
    try:
        for value in vars(sample).values():
            if isinstance(value, (str, Path)) and os.path.isfile(str(value)):
                return str(Path(os.path.realpath(value)))
    except TypeError:
        pass
    return None


def is_loaded(path):
    loaded = _state['loaded']
    return bool(loaded and path is not None and os.path.realpath(path) == loaded)


def _selected():
    browser, entry = _state['browser'], _state['entry']
    if browser is None or time.monotonic() > _state['visible_until']:
        return None
    return _entry_path(browser, entry)


def _ru(ui):
    return str(getattr(ui, 'info_language', 'EN')).upper() == 'RU'


def _delete(path):
    if is_loaded(path):
        return
    try:
        os.remove(path)
    except OSError as exc:
        _log('delete failed: %s: %r' % (path, exc))
        _state['message'] = 'DELETE ERROR'
        _state['message_until'] = time.monotonic() + 2
        return
    _log('deleted ' + str(path))
    _state['message'] = 'DELETED: ' + Path(path).name
    _state['message_until'] = time.monotonic() + 2
    controller = _state['controller']
    try:
        if controller is not None and hasattr(controller, 'request_sample_refresh'):
            controller.request_sample_refresh()
        elif _state['browser'] is not None:
            _state['browser'].refresh()
    except Exception as exc:  # never break the app because of a refresh
        _log('refresh failed: %r' % exc)


def _attach():
    modules = [sys.modules.get(n) for n in ('engine.sample_browser', 'engine.input',
                                            'ui.renderer', 'engine.control')]
    if any(m is None for m in modules):
        return False
    browser_mod, input_mod, renderer_mod, control_mod = modules
    Browser = getattr(browser_mod, 'SampleBrowser', None)
    UI, Input, Control = renderer_mod.UIEngine, input_mod.InputManager, control_mod.ControlManager
    if Browser is None or not hasattr(Browser, 'get') or not hasattr(UI, 'draw_sample_page'):
        _log('unsupported engine; sample deletion disabled')
        return True
    old_get, old_draw, old_poll, old_ctl = Browser.get, UI.draw_sample_page, Input.poll, Control.__init__
    old_set_sample = getattr(UI, 'set_sample', None)

    def set_sample(self, sample, *args, **kwargs):
        _state['loaded'] = _sample_path(sample) or _state.get('pending_load') or _state['loaded']
        _log('loaded sample: %s' % _state['loaded'])
        return old_set_sample(self, sample, *args, **kwargs)

    def ctl_init(self, *args, **kwargs):
        old_ctl(self, *args, **kwargs)
        _state['controller'] = self

    def get(self, index, *args, **kwargs):
        entry = old_get(self, index, *args, **kwargs)
        if _state['index'] != index:
            _state['armed'] = None
        _state.update(browser=self, index=index, entry=entry)
        return entry

    def draw(self, *args, **kwargs):
        result = old_draw(self, *args, **kwargs)
        _state['visible_until'] = time.monotonic() + 0.3
        path = _selected()
        now = time.monotonic()
        text, color = None, self.DIM
        if now < _state['message_until']:
            text, color = _state['message'], self.ACCENT
            if _ru(self):
                text = text.replace('DELETED:', 'УДАЛЕНО:').replace('DELETE ERROR', 'ОШИБКА УДАЛЕНИЯ')
        elif deletable(path) and is_loaded(path):
            text = 'ЗАГРУЖЕНА — НЕЛЬЗЯ УДАЛИТЬ' if _ru(self) else 'LOADED - CANNOT DELETE'
        elif deletable(path):
            armed = _state['armed'] == str(path) and now - _state['armed_at'] < CONFIRM_SECONDS
            if armed:
                text = ('SELECT ЕЩЁ РАЗ: УДАЛИТЬ ' if _ru(self) else 'SELECT AGAIN: DELETE ') + Path(path).name
                color = self.ACCENT
            else:
                text = 'SELECT: УДАЛИТЬ ЗАПИСЬ' if _ru(self) else 'SELECT: DELETE RECORDING'
        if text:
            pygame.draw.rect(self.screen, self.BG, (0, 652, self.WIDTH, 36))
            self.text(text[:60], 54, 658, scale=2, color=color)
        return result

    def poll(self, *args, **kwargs):
        result = old_poll(self, *args, **kwargs)
        if not result:
            return result
        path = _selected()
        if path is not None and any(act == 'A' for act, v in result) and os.path.isfile(str(path)):
            # Fallback when the sample object exposes no path: A loads this file.
            _state['pending_load'] = str(Path(os.path.realpath(path)))
        if not deletable(path):
            return result
        if is_loaded(path):
            # Protect the playing sample: swallow SELECT, show the hint only.
            return [(a, v) for a, v in result if a != 'SELECT']
        actions = [a for a, v in result]
        if 'SELECT' not in actions:
            if any(a in ('UP', 'DOWN', 'LEFT', 'RIGHT', 'A', 'B', 'X', 'Y') for a in actions):
                _state['armed'] = None
            return result
        now = time.monotonic()
        if _state['armed'] == str(path) and now - _state['armed_at'] < CONFIRM_SECONDS:
            _state['armed'] = None
            _delete(path)
        else:
            _state['armed'], _state['armed_at'] = str(path), now
        return [(a, v) for a, v in result if a != 'SELECT']

    Browser.get, UI.draw_sample_page, Input.poll, Control.__init__ = get, draw, poll, ctl_init
    if old_set_sample is not None:
        UI.set_sample = set_sample
    _log('installed (SELECT twice deletes a recording)')
    return True


def install():
    if os.environ.get('GRAINBERNIK_SAMPLE_DELETE', '1') == '0':
        return
    original_init = pygame.init
    done = [False]

    def init(*args, **kwargs):
        if not done[0]:
            done[0] = _attach()
        return original_init(*args, **kwargs)

    pygame.init = init
