"""Region picker with live low-LOD world preview behind the overlay."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QPushButton, QVBoxLayout, QWidget

from ..config.settings import UserSettings
from ..i18n import t
from ..world_gen.world_profile import WorldProfile
from .theme import scale_px

REGION_ORDER = ("coast", "mountains", "forest", "desert", "industrial")


class RegionSelectView(QWidget):
    selected = Signal(str)
    back = Signal()
    preview = Signal(str)

    def __init__(self, settings: UserSettings, parent=None) -> None:
        super().__init__(parent)
        self.settings = settings
        self.profiles: list[WorldProfile] = []
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        root = QHBoxLayout(self)
        root.setContentsMargins(56, 48, 56, 48)
        left = QVBoxLayout()
        head = QHBoxLayout()
        self.heading = QLabel("")
        self.heading.setObjectName("Title")
        self.back_btn = QPushButton("")
        self.back_btn.setObjectName("GhostBtn")
        self.back_btn.clicked.connect(self.back.emit)
        head.addWidget(self.heading)
        head.addStretch(1)
        head.addWidget(self.back_btn)
        left.addLayout(head)
        self.list = QListWidget()
        self.list.currentRowChanged.connect(self._on_row)
        left.addWidget(self.list, 1)
        root.addLayout(left, 1)
        right = QVBoxLayout()
        self.name = QLabel("")
        self.name.setObjectName("Title")
        self.meta = QLabel("")
        self.meta.setObjectName("Muted")
        self.btn = QPushButton("")
        self.btn.setObjectName("PrimaryBtn")
        self.btn.clicked.connect(self._fly)
        right.addWidget(self.name)
        right.addWidget(self.meta)
        right.addStretch(1)
        right.addWidget(self.btn, 0, Qt.AlignLeft)
        root.addLayout(right, 1)
        self.retranslate()
        self.relayout()

    def set_profiles(self, profiles: list[WorldProfile], current_id: str) -> None:
        by_id = {p.id: p for p in profiles}
        ordered = [by_id[k] for k in REGION_ORDER if k in by_id]
        ordered.extend(p for p in profiles if p.id not in REGION_ORDER)
        self.profiles = ordered
        self.list.blockSignals(True)
        self.list.clear()
        sel = 0
        for i, p in enumerate(self.profiles):
            QListWidgetItem(p.name, self.list)
            if p.id == current_id:
                sel = i
        self.list.blockSignals(False)
        self.list.setCurrentRow(sel)
        self._on_row(sel)

    def current(self) -> WorldProfile | None:
        i = self.list.currentRow()
        if 0 <= i < len(self.profiles):
            return self.profiles[i]
        return None

    def _on_row(self, row: int) -> None:
        if not (0 <= row < len(self.profiles)):
            return
        p = self.profiles[row]
        self.name.setText(p.name)
        self.meta.setText(f"SEED SALT  {p.seed_salt}\nRIVERS  {p.river_threshold:.0f}\nSETTLEMENTS  {p.settlement_count}")
        self.preview.emit(p.id)

    def _fly(self) -> None:
        p = self.current()
        if p is not None:
            self.selected.emit(p.id)

    def retranslate(self) -> None:
        self.heading.setText(t("regions"))
        self.back_btn.setText(t("back"))
        self.btn.setText(t("fly"))

    def relayout(self) -> None:
        s = self.settings
        self.heading.setStyleSheet(f"font-size:{scale_px(self, s, 22)}px; letter-spacing:4px;")
        self.name.setStyleSheet(f"font-size:{scale_px(self, s, 28)}px;")
        self.meta.setStyleSheet(f"font-size:{scale_px(self, s, 14)}px;")
