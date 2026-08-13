"""Resolve UserSettings control bindings to Qt keys / action names."""

from __future__ import annotations

from PySide6.QtCore import Qt

from .config.settings import DEFAULT_BINDINGS

_NAME = {
    "SHIFT": Qt.Key_Shift,
    "CTRL": Qt.Key_Control,
    "CONTROL": Qt.Key_Control,
    "SPACE": Qt.Key_Space,
    "ESC": Qt.Key_Escape,
    "ESCAPE": Qt.Key_Escape,
    "BACKSPACE": Qt.Key_Backspace,
    "TAB": Qt.Key_Tab,
    "ALT": Qt.Key_Alt,
}

for _ch in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
    _NAME[_ch] = getattr(Qt, f"Key_{_ch}")
for _n in range(10):
    _NAME[str(_n)] = getattr(Qt, f"Key_{_n}")


def parse_key(name: str) -> int | None:
    key = (name or "").strip().upper()
    if not key:
        return None
    if key in _NAME:
        return int(_NAME[key])
    if len(key) == 1:
        attr = f"Key_{key}"
        if hasattr(Qt, attr):
            return int(getattr(Qt, attr))
    return None


def bindings_map(raw: dict[str, str] | None) -> dict[int, str]:
    merged = dict(DEFAULT_BINDINGS)
    merged.update(raw or {})
    out: dict[int, str] = {}
    for action, name in merged.items():
        code = parse_key(name)
        if code is not None:
            out[code] = action
    return out
