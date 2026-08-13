"""Cinematic / photo mode. Visual TOD override only — recorded flight stays honest."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QSlider, QVBoxLayout, QWidget

from ..config.settings import UserSettings
from ..i18n import t
from .theme import scale_px


class CinematicView(QWidget):
    closed = Signal()
    screenshot = Signal()
    fov = Signal(int)
    tod = Signal(float)
    reset_tod = Signal()

    def __init__(self, settings: UserSettings, parent=None) -> None:
        super().__init__(parent)
        self.cfg = settings
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(48, 36, 48, 36)
        self.title = QLabel("CINEMATIC MODE")
        self.title.setObjectName("Title")
        self.sub = QLabel("FLIGHT PAUSED    visual TOD override")
        self.sub.setObjectName("Muted")
        lay.addWidget(self.title)
        lay.addWidget(self.sub)
        row = QHBoxLayout()
        self.fov_s = QSlider(Qt.Horizontal)
        self.fov_s.setRange(40, 110)
        self.fov_s.setValue(80)
        self.fov_s.valueChanged.connect(self.fov.emit)
        self.tod_s = QSlider(Qt.Horizontal)
        self.tod_s.setRange(0, 239)
        self.tod_s.setValue(120)
        self.tod_s.valueChanged.connect(lambda v: self.tod.emit(v / 10.0))
        row.addWidget(QLabel("FOV"))
        row.addWidget(self.fov_s)
        row.addWidget(QLabel("TOD"))
        row.addWidget(self.tod_s)
        lay.addLayout(row)
        btns = QHBoxLayout()
        self.shot = QPushButton("SCREENSHOT")
        self.shot.setObjectName("PrimaryBtn")
        self.shot.clicked.connect(self.screenshot.emit)
        self.reset = QPushButton("RESET TOD")
        self.reset.setObjectName("GhostBtn")
        self.reset.clicked.connect(self.reset_tod.emit)
        self.back = QPushButton("BACK")
        self.back.setObjectName("GhostBtn")
        self.back.clicked.connect(self.closed.emit)
        btns.addWidget(self.shot)
        btns.addWidget(self.reset)
        btns.addStretch(1)
        btns.addWidget(self.back)
        lay.addLayout(btns)
        lay.addStretch(1)
        self.relayout()

    def relayout(self) -> None:
        s = self.cfg
        self.title.setStyleSheet(f"font-size:{scale_px(self, s, 22)}px; letter-spacing:4px;")
        self.sub.setStyleSheet(f"font-size:{scale_px(self, s, 13)}px;")
