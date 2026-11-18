"""Shared registry for extra rows in the BETA 2.0 SETTINGS list.

ControlManager.SETTINGS_PARAMS (keys) and the renderer rows
(UIEngine.gb_extra_settings_rows) must stay aligned. Every GrainBernik page
registers here, so keys and rows are appended in the same order no matter
which adapter draws first. Entries go after the native RHYTHM/BLE rows.
"""

_entries = []          # [(key, label, value_fn)]


def register(control_cls, ui, key, label, value_fn):
    """Idempotent. Call lazily (first draw), after the native integration ran."""
    if not any(e[0] == key for e in _entries):
        _entries.append((key, label, value_fn))
    params = list(control_cls.SETTINGS_PARAMS)
    for entry in _entries:
        if entry[0] not in params:
            params.append(entry[0])
    control_cls.SETTINGS_PARAMS = params
    if ui is not None and not getattr(ui, '_gb_rows_registry', False):
        previous = getattr(ui, 'gb_extra_settings_rows', None)

        def extra_rows(controls, previous=previous):
            rows = list(previous(controls)) if previous is not None else []
            for k, lab, fn in _entries:
                try:
                    value = fn()
                except Exception:
                    value = '>'
                rows.append((k, lab, value))
            return rows
        ui.gb_extra_settings_rows = extra_rows
        ui._gb_rows_registry = True


_info = {}


def register_info(ui_cls, renderer, key, provider):
    """Own INFO text for a SETTINGS row: provider(language) -> (title, text).

    BETA 2.0 layers (ORBIX Rings / OSCILLATOR info) replace
    ui.renderer.get_context_info AFTER our adapters attached, so patching that
    name is not enough. UIEngine.draw_info_window is wrapped instead and swaps
    the lookup for the duration of the call.
    """
    _info[key] = provider
    if getattr(ui_cls, '_gb_info_registry', False):
        return
    previous = ui_cls.draw_info_window

    def draw_info_window(self, param, *args, **kwargs):
        provider = _info.get(param)
        if provider is None:
            return previous(self, param, *args, **kwargs)
        native = renderer.get_context_info

        def lookup(name, language='EN', *rest, **more):
            if name == param:
                try:
                    return provider(language)
                except Exception:
                    pass
            return native(name, language, *rest, **more)
        renderer.get_context_info = lookup
        try:
            return previous(self, param, *args, **kwargs)
        finally:
            renderer.get_context_info = native

    ui_cls.draw_info_window = draw_info_window
    ui_cls._gb_info_registry = True


def reset():
    """Tests only."""
    _entries.clear()
    _info.clear()
