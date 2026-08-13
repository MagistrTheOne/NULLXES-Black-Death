"""Loading overlay — hangar art + stage labels, no fake percent."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from ..config.settings import UserSettings
from ..i18n import t
from .backdrop import paint_menu_art
from .theme import scale_px

STAGE_KEYS = ("aircraft", "world", "vision", "mission")


class LoadingView(QWidget):
    def __init__(self, settings: UserSettings, parent=None) -> None:
        super().__init__(parent)
        self.settings = settings
        self._current = "aircraft"
        self._detail_key = "load_visual"
        self.setAutoFillBackground(False)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(80, 80, 80, 80)
        lay.addStretch(1)
        self.brand = QLabel("NULLXES BLACKBOX")
        self.brand.setObjectName("Title")
        self.sub = QLabel("")
        self.sub.setObjectName("Muted")
        lay.addWidget(self.brand)
        lay.addWidget(self.sub)
        lay.addSpacing(28)
        self.labels: dict[str, QLabel] = {}
        for key in STAGE_KEYS:
            lab = QLabel("")
            lab.setObjectName("Muted")
            self.labels[key] = lab
            lay.addWidget(lab)
        self.detail = QLabel("")
        self.detail.setObjectName("Muted")
        lay.addSpacing(16)
        lay.addWidget(self.detail)
        lay.addStretch(2)
        self.retranslate()
        self.relayout()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        paint_menu_art(self, painter, left_vignette=True, dim=0.22)
        painter.end()
        super().paintEvent(event)

    def retranslate(self) -> None:
        self.sub.setText(t("init_env"))
        self.set_stage(self._current, self._detail_key)

    def relayout(self) -> None:
        s = self.settings
        self.brand.setStyleSheet(f"font-size:{scale_px(self, s, 28)}px;")
        self.sub.setStyleSheet(f"font-size:{scale_px(self, s, 13)}px; letter-spacing:3px;")
        for lab in self.labels.values():
            lab.setStyleSheet(f"font-size:{scale_px(self, s, 14)}px;")

    def set_stage(self, current: str, detail: str = "") -> None:
        key = current.lower()
        if key.startswith("stage_"):
            key = key[6:]
        self._current = key if key in self.labels else "aircraft"
        self._detail_key = detail if detail.startswith("load_") else detail
        hit = False
        for name, lab in self.labels.items():
            title = t(f"stage_{name}")
            if name == self._current:
                lab.setText(f"●  {title}")
                lab.setStyleSheet(f"color:#F2F2F2; font-size:{scale_px(self, self.settings, 14)}px;")
                hit = True
            elif not hit:
                lab.setText(f"  {title}")
                lab.setStyleSheet(f"color:#8A8A8E; font-size:{scale_px(self, self.settings, 14)}px;")
            else:
                lab.setText(f"  {title}")
        detail_text = t(self._detail_key) if self._detail_key.startswith("load_") else self._detail_key
        self.detail.setText(detail_text)
