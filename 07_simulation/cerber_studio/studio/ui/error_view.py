"""Product error overlay."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget

from ..config.settings import UserSettings
from ..i18n import t
from .theme import scale_px


class ErrorView(QWidget):
    fallback = Signal()
    back = Signal()

    def __init__(self, settings: UserSettings, parent=None) -> None:
        super().__init__(parent)
        self.settings = settings
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(80, 80, 80, 80)
        lay.addStretch(1)
        self.title = QLabel("")
        self.title.setObjectName("Title")
        self.body = QLabel("")
        self.body.setObjectName("Muted")
        self.body.setWordWrap(True)
        self.btn_fb = QPushButton("")
        self.btn_fb.setObjectName("PrimaryBtn")
        self.btn_back = QPushButton("")
        self.btn_back.setObjectName("GhostBtn")
        self.btn_fb.clicked.connect(self.fallback.emit)
        self.btn_back.clicked.connect(self.back.emit)
        lay.addWidget(self.title)
        lay.addWidget(self.body)
        lay.addSpacing(20)
        lay.addWidget(self.btn_fb, 0, Qt.AlignLeft)
        lay.addWidget(self.btn_back, 0, Qt.AlignLeft)
        lay.addStretch(2)
        self.retranslate()

    def retranslate(self) -> None:
        self.btn_fb.setText(t("use_fallback"))
        self.btn_back.setText(t("return_aircraft"))

    def show_error(self, title: str, body: str, *, fallback: bool) -> None:
        self.title.setText(title)
        self.body.setText(body)
        self.btn_fb.setVisible(fallback)
        s = self.settings
        self.title.setStyleSheet(f"font-size:{scale_px(self, s, 22)}px;")
        self.body.setStyleSheet(f"font-size:{scale_px(self, s, 14)}px;")
