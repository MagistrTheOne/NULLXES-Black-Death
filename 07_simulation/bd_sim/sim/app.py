"""Fullscreen product demo window."""

from __future__ import annotations

from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import QMainWindow

from .engine import SimViewport


class SimWindow(QMainWindow):
    def __init__(self, *, cerber: bool = False) -> None:
        super().__init__()
        self.setWindowTitle("NULLXES BD-SIM S1 — arcade flying-wing — NOT TWIN")
        self.view = SimViewport(self)
        self.setCentralWidget(self.view)
        if cerber:
            self.view.engine.cerber.start()
        self.resize(1280, 720)
        self.view.setFocus()

    def closeEvent(self, event: QCloseEvent) -> None:
        self.view.engine.close_engine()
        super().closeEvent(event)
