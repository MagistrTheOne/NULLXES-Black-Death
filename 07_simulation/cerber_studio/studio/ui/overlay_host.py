"""Overlay that forwards empty-space mouse events to the 3D viewport."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QMouseEvent, QWheelEvent
from PySide6.QtWidgets import (
    QAbstractButton,
    QAbstractSlider,
    QAbstractSpinBox,
    QCheckBox,
    QComboBox,
    QLineEdit,
    QListWidget,
    QScrollArea,
    QWidget,
)

_INTERACTIVE = (
    QAbstractButton,
    QAbstractSlider,
    QAbstractSpinBox,
    QCheckBox,
    QComboBox,
    QLineEdit,
    QListWidget,
    QScrollArea,
)


class OverlayHost(QWidget):
    def __init__(self, viewport: QWidget, parent=None) -> None:
        super().__init__(parent)
        self.viewport = viewport
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAutoFillBackground(False)

    def _over_interactive(self, pos) -> bool:
        child = self.childAt(pos)
        cur = child
        while cur is not None and cur is not self:
            if isinstance(cur, _INTERACTIVE):
                return True
            cur = cur.parentWidget()
        return False

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if not self._over_interactive(event.position().toPoint()):
            self.viewport.mousePressEvent(event)
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if not self._over_interactive(event.position().toPoint()):
            self.viewport.mouseMoveEvent(event)
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        self.viewport.mouseReleaseEvent(event)
        super().mouseReleaseEvent(event)

    def wheelEvent(self, event: QWheelEvent) -> None:
        if not self._over_interactive(event.position().toPoint()):
            self.viewport.wheelEvent(event)
            return
        super().wheelEvent(event)

    def event(self, event: QEvent) -> bool:
        return super().event(event)
