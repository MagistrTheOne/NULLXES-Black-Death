"""Region picker with dedicated lightweight preview — not the flight world."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QPushButton, QVBoxLayout, QWidget

from ..config.settings import UserSettings
from ..i18n import t
from ..world_gen.world_profile import WorldProfile
from .theme import scale_px

REGION_ORDER = ("coast", "mountains", "forest", "desert", "industrial", "arctic", "steppe")


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
        root.setContentsMargins(40, 36, 40, 36)
        root.setSpacing(24)

        left = QWidget()
        left.setObjectName("GlassPanel")
        left.setFixedWidth(320)
        ll = QVBoxLayout(left)
        ll.setContentsMargins(22, 20, 22, 20)
        self.brand = QLabel("NULLXES BLACKBOX")
        self.brand.setObjectName("Brand")
        self.heading = QLabel("")
        self.heading.setObjectName("Title")
        ll.addWidget(self.brand)
        ll.addWidget(self.heading)
        self.list = QListWidget()
        self.list.currentRowChanged.connect(self._on_row)
        ll.addWidget(self.list, 1)
        self.back_btn = QPushButton("")
        self.back_btn.setObjectName("GhostBtn")
        self.back_btn.clicked.connect(self.back.emit)
        ll.addWidget(self.back_btn, 0, Qt.AlignLeft)
        root.addWidget(left, 0)

        right = QVBoxLayout()
        right.addStretch(1)
        card = QWidget()
        card.setObjectName("GlassPanel")
        cl = QVBoxLayout(card)
        cl.setContentsMargins(28, 24, 28, 24)
        self.name = QLabel("")
        self.name.setObjectName("Title")
        self.meta = QLabel("")
        self.meta.setObjectName("Muted")
        self.btn = QPushButton("")
        self.btn.setObjectName("PrimaryBtn")
        self.btn.clicked.connect(self._fly)
        cl.addWidget(self.name)
        cl.addWidget(self.meta)
        cl.addSpacing(12)
        cl.addWidget(self.btn, 0, Qt.AlignLeft)
        right.addWidget(card, 0, Qt.AlignRight)
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
        seed = int(self.settings.session.world_seed)
        terrain = (p.terrain_label or p.material_id or p.name).upper()
        weather = (p.sky_preset or "clear").upper()
        clock = 14.5 if p.sky_preset != "night" else 22.0
        hh = int(clock)
        mm = int((clock % 1.0) * 60)
        self.meta.setText(
            f"{t('seed'):<10} {seed}\n"
            f"{t('terrain_label'):<10} {terrain}\n"
            f"{t('weather_label'):<10} {weather}\n"
            f"{t('time_label'):<10} {hh:02d}:{mm:02d}"
        )
        self.preview.emit(p.id)

    def _fly(self) -> None:
        p = self.current()
        if p is not None:
            self.selected.emit(p.id)

    def retranslate(self) -> None:
        self.heading.setText(t("regions"))
        self.back_btn.setText(t("back"))
        self.btn.setText(t("choose"))
        p = self.current()
        if p is not None:
            self._on_row(self.list.currentRow())

    def relayout(self) -> None:
        s = self.settings
        self.brand.setStyleSheet(f"font-size:{scale_px(self, s, 12)}px; letter-spacing:5px;")
        self.heading.setStyleSheet(f"font-size:{scale_px(self, s, 22)}px; letter-spacing:4px;")
        self.name.setStyleSheet(f"font-size:{scale_px(self, s, 28)}px;")
        self.meta.setStyleSheet(f"font-size:{scale_px(self, s, 14)}px;")
