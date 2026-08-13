"""Product main menu."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from ..config.settings import UserSettings
from .theme import scale_px


class MainMenuView(QWidget):
    start = Signal()
    aircraft = Signal()
    mission = Signal()
    settings = Signal()
    exit_app = Signal()

    def __init__(self, settings: UserSettings, version: str, parent=None) -> None:
        super().__init__(parent)
        self.settings = settings
        self.version = version
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        root = QHBoxLayout(self)
        root.setContentsMargins(72, 64, 72, 48)
        col = QVBoxLayout()
        col.setSpacing(10)
        self.brand = QLabel("NULLXES")
        self.brand.setObjectName("Brand")
        self.title = QLabel("CERBER STUDIO")
        self.title.setObjectName("Title")
        self.sub = QLabel("FLIGHT SIMULATION")
        self.sub.setObjectName("Muted")
        col.addWidget(self.brand)
        col.addWidget(self.title)
        col.addWidget(self.sub)
        col.addSpacing(28)
        self.btn_start = self._btn("START", primary=True)
        self.btn_ac = self._btn("AIRCRAFT")
        self.btn_ms = self._btn("MISSION")
        self.btn_st = self._btn("SETTINGS")
        self.btn_ex = self._btn("EXIT")
        self.btn_start.clicked.connect(self.start.emit)
        self.btn_ac.clicked.connect(self.aircraft.emit)
        self.btn_ms.clicked.connect(self.mission.emit)
        self.btn_st.clicked.connect(self.settings.emit)
        self.btn_ex.clicked.connect(self.exit_app.emit)
        for b in (self.btn_start, self.btn_ac, self.btn_ms, self.btn_st, self.btn_ex):
            col.addWidget(b)
        col.addStretch(1)
        self.status = QLabel()
        self.status.setObjectName("Muted")
        self.build = QLabel(f"BUILD {version}")
        self.build.setObjectName("Muted")
        col.addWidget(self.status)
        col.addWidget(self.build)
        root.addLayout(col, 0)
        root.addStretch(1)
        self.relayout()

    def _btn(self, text: str, primary: bool = False) -> QPushButton:
        b = QPushButton(text)
        b.setObjectName("PrimaryBtn" if primary else "MenuBtn")
        b.setCursor(Qt.PointingHandCursor)
        return b

    def relayout(self) -> None:
        s = self.settings
        self.brand.setStyleSheet(f"font-size:{scale_px(self, s, 12)}px; letter-spacing:6px;")
        self.title.setStyleSheet(f"font-size:{scale_px(self, s, 36)}px;")
        self.sub.setStyleSheet(f"font-size:{scale_px(self, s, 13)}px; letter-spacing:3px;")
        pad = scale_px(self, s, 14)
        for b in (self.btn_start, self.btn_ac, self.btn_ms, self.btn_st, self.btn_ex):
            b.setFixedWidth(scale_px(self, s, 280))
            b.setStyleSheet(b.styleSheet() + f" font-size:{scale_px(self, s, 15)}px; padding:{pad}px {pad + 8}px;")
        self.status.setStyleSheet(f"font-size:{scale_px(self, s, 11)}px;")
        self.build.setStyleSheet(f"font-size:{scale_px(self, s, 11)}px;")

    def set_health(self, cerber: str, vision: str, sim: str) -> None:
        self.status.setText(f"CERBER     {cerber}        VISION     {vision}        SIM        {sim}")
