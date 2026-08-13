"""Boot splash."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from ..config.settings import UserSettings
from .theme import scale_px


class SplashView(QWidget):
    def __init__(self, settings: UserSettings, parent=None) -> None:
        super().__init__(parent)
        self.settings = settings
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(80, 80, 80, 80)
        lay.addStretch(1)
        self.brand = QLabel("NULLXES")
        self.brand.setObjectName("Brand")
        self.brand.setAlignment(Qt.AlignCenter)
        self.title = QLabel("CERBER STUDIO")
        self.title.setObjectName("Title")
        self.title.setAlignment(Qt.AlignCenter)
        self.stage = QLabel("INITIALIZING")
        self.stage.setObjectName("Muted")
        self.stage.setAlignment(Qt.AlignCenter)
        lay.addWidget(self.brand)
        lay.addWidget(self.title)
        lay.addSpacing(24)
        lay.addWidget(self.stage)
        lay.addStretch(1)
        self.relayout()

    def relayout(self) -> None:
        s = self.settings
        self.brand.setStyleSheet(f"font-size:{scale_px(self, s, 14)}px; letter-spacing:8px;")
        self.title.setStyleSheet(f"font-size:{scale_px(self, s, 42)}px;")
        self.stage.setStyleSheet(f"font-size:{scale_px(self, s, 13)}px;")

    def set_stage(self, text: str) -> None:
        self.stage.setText(text)
