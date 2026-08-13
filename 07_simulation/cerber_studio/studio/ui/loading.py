"""Loading overlay — stage labels, no fake percent."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from ..config.settings import UserSettings
from .theme import scale_px

STAGES = ("AIRCRAFT", "WORLD", "VISION", "MISSION")


class LoadingView(QWidget):
    def __init__(self, settings: UserSettings, parent=None) -> None:
        super().__init__(parent)
        self.settings = settings
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(80, 80, 80, 80)
        lay.addStretch(1)
        self.brand = QLabel("CERBER STUDIO")
        self.brand.setObjectName("Title")
        self.sub = QLabel("INITIALIZING FLIGHT ENVIRONMENT")
        self.sub.setObjectName("Muted")
        lay.addWidget(self.brand)
        lay.addWidget(self.sub)
        lay.addSpacing(28)
        self.labels: dict[str, QLabel] = {}
        for name in STAGES:
            lab = QLabel(name)
            lab.setObjectName("Muted")
            self.labels[name] = lab
            lay.addWidget(lab)
        self.detail = QLabel("")
        self.detail.setObjectName("Muted")
        lay.addSpacing(16)
        lay.addWidget(self.detail)
        lay.addStretch(2)
        self.relayout()

    def relayout(self) -> None:
        s = self.settings
        self.brand.setStyleSheet(f"font-size:{scale_px(self, s, 28)}px;")
        self.sub.setStyleSheet(f"font-size:{scale_px(self, s, 13)}px; letter-spacing:3px;")
        for lab in self.labels.values():
            lab.setStyleSheet(f"font-size:{scale_px(self, s, 14)}px;")

    def set_stage(self, current: str, detail: str = "") -> None:
        hit = False
        for name, lab in self.labels.items():
            if name == current:
                lab.setText(f"●  {name}")
                lab.setStyleSheet(f"color:#F2F2F2; font-size:{scale_px(self, self.settings, 14)}px;")
                hit = True
            elif not hit:
                lab.setText(f"  {name}")
                lab.setStyleSheet(f"color:#8A8A8E; font-size:{scale_px(self, self.settings, 14)}px;")
            else:
                lab.setText(f"  {name}")
        self.detail.setText(detail)
