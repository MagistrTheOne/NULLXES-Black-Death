"""In-simulation pause overlay."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget

from ..config.settings import UserSettings
from .theme import scale_px


class PauseMenuView(QWidget):
    resume = Signal()
    restart = Signal()
    settings = Signal()
    aircraft = Signal()
    main_menu = Signal()
    exit_app = Signal()

    def __init__(self, settings: UserSettings, parent=None) -> None:
        super().__init__(parent)
        self.settings = settings
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(80, 80, 80, 80)
        lay.addStretch(1)
        self.title = QLabel("PAUSED")
        self.title.setObjectName("Title")
        lay.addWidget(self.title)
        lay.addSpacing(20)
        self.buttons = []
        for text, sig in (
            ("RESUME", self.resume),
            ("RESTART MISSION", self.restart),
            ("SETTINGS", self.settings),
            ("AIRCRAFT", self.aircraft),
            ("MAIN MENU", self.main_menu),
            ("EXIT", self.exit_app),
        ):
            b = QPushButton(text)
            b.setObjectName("MenuBtn")
            b.setCursor(Qt.PointingHandCursor)
            b.clicked.connect(sig.emit)
            lay.addWidget(b)
            self.buttons.append(b)
        lay.addStretch(2)
        self.relayout()

    def relayout(self) -> None:
        s = self.settings
        self.title.setStyleSheet(f"font-size:{scale_px(self, s, 32)}px; letter-spacing:6px;")
        w = scale_px(self, s, 320)
        for b in self.buttons:
            b.setFixedWidth(w)
            b.setStyleSheet(f"font-size:{scale_px(self, s, 15)}px;")
