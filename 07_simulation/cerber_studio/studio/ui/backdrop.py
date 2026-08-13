"""Cover-scale hangar art behind product UI."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPixmap
from PySide6.QtWidgets import QWidget

from ..config.paths import menu_background_path

_CACHE: QPixmap | None = None


def menu_art() -> QPixmap:
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    path = menu_background_path()
    _CACHE = QPixmap(str(path)) if path is not None else QPixmap()
    return _CACHE


def paint_menu_art(
    widget: QWidget,
    painter: QPainter,
    *,
    left_vignette: bool = True,
    dim: float = 0.0,
) -> None:
    art = menu_art()
    painter.fillRect(widget.rect(), QColor(8, 8, 9))
    if not art.isNull():
        scaled = art.scaled(
            widget.size(),
            Qt.KeepAspectRatioByExpanding,
            Qt.SmoothTransformation,
        )
        x = (widget.width() - scaled.width()) // 2
        y = (widget.height() - scaled.height()) // 2
        painter.drawPixmap(x, y, scaled)
    if dim > 0.0:
        painter.fillRect(widget.rect(), QColor(0, 0, 0, int(220 * min(1.0, dim))))
    if left_vignette:
        fade = QLinearGradient(0, 0, min(widget.width() * 0.52, 820), 0)
        fade.setColorAt(0.0, QColor(0, 0, 0, 170))
        fade.setColorAt(0.55, QColor(0, 0, 0, 70))
        fade.setColorAt(1.0, QColor(0, 0, 0, 0))
        painter.fillRect(widget.rect(), fade)
