"""Aircraft selection with live Panda3D preview (viewport behind overlay)."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..aircraft.definition import AircraftDefinition
from ..config.settings import UserSettings
from .theme import scale_px


class AircraftSelectView(QWidget):
    prev_ac = Signal()
    next_ac = Signal()
    select = Signal()
    back = Signal()
    reset_view = Signal()
    slot_ego = Signal()
    slot_target = Signal()

    def __init__(self, settings: UserSettings, parent=None) -> None:
        super().__init__(parent)
        self.settings = settings
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        root = QVBoxLayout(self)
        root.setContentsMargins(56, 40, 56, 40)

        top = QHBoxLayout()
        self.heading = QLabel("AIRCRAFT")
        self.heading.setObjectName("Title")
        self.back_btn = QPushButton("BACK")
        self.back_btn.setObjectName("GhostBtn")
        self.back_btn.clicked.connect(self.back.emit)
        top.addWidget(self.heading)
        top.addStretch(1)
        top.addWidget(self.back_btn)
        root.addLayout(top)

        slots = QHBoxLayout()
        self.btn_ego = QPushButton("EGO AIRCRAFT")
        self.btn_tgt = QPushButton("TARGET")
        self.btn_ego.setObjectName("GhostBtn")
        self.btn_tgt.setObjectName("GhostBtn")
        self.btn_ego.clicked.connect(self.slot_ego.emit)
        self.btn_tgt.clicked.connect(self.slot_target.emit)
        self.ego_name = QLabel("—")
        self.tgt_name = QLabel("—")
        self.ego_name.setObjectName("Muted")
        self.tgt_name.setObjectName("Muted")
        slots.addWidget(self.btn_ego)
        slots.addWidget(self.ego_name)
        slots.addSpacing(24)
        slots.addWidget(self.btn_tgt)
        slots.addWidget(self.tgt_name)
        slots.addStretch(1)
        root.addLayout(slots)
        root.addStretch(1)

        nav = QHBoxLayout()
        self.btn_prev = QPushButton("<  PREV")
        self.btn_next = QPushButton("NEXT  >")
        self.btn_prev.setObjectName("GhostBtn")
        self.btn_next.setObjectName("GhostBtn")
        self.btn_prev.clicked.connect(self.prev_ac.emit)
        self.btn_next.clicked.connect(self.next_ac.emit)
        nav.addWidget(self.btn_prev)
        nav.addStretch(1)
        nav.addWidget(self.btn_next)
        root.addLayout(nav)

        self.name = QLabel("")
        self.name.setObjectName("Title")
        self.klass = QLabel("")
        self.klass.setObjectName("Muted")
        self.warn = QLabel("")
        self.warn.setObjectName("Muted")
        self.stats = QLabel("")
        self.stats.setObjectName("Muted")
        root.addWidget(self.name)
        root.addWidget(self.klass)
        root.addWidget(self.warn)
        root.addWidget(self.stats)

        bottom = QHBoxLayout()
        self.btn_reset = QPushButton("RESET VIEW")
        self.btn_reset.setObjectName("GhostBtn")
        self.btn_reset.clicked.connect(self.reset_view.emit)
        self.btn_select = QPushButton("SELECT")
        self.btn_select.setObjectName("PrimaryBtn")
        self.btn_select.clicked.connect(self.select.emit)
        bottom.addWidget(self.btn_reset)
        bottom.addStretch(1)
        bottom.addWidget(self.btn_select)
        root.addLayout(bottom)
        self.relayout()

    def relayout(self) -> None:
        s = self.settings
        self.heading.setStyleSheet(f"font-size:{scale_px(self, s, 22)}px; letter-spacing:4px;")
        self.name.setStyleSheet(f"font-size:{scale_px(self, s, 28)}px;")
        self.klass.setStyleSheet(f"font-size:{scale_px(self, s, 13)}px; letter-spacing:2px;")
        self.stats.setStyleSheet(f"font-size:{scale_px(self, s, 13)}px;")
        self.warn.setStyleSheet(f"font-size:{scale_px(self, s, 12)}px; color:#C4C4C4;")

    def set_slot(self, slot: str, ego_name: str, tgt_name: str) -> None:
        self.ego_name.setText(ego_name)
        self.tgt_name.setText(tgt_name)
        self.btn_ego.setText("EGO AIRCRAFT" + ("  ●" if slot == "ego" else ""))
        self.btn_tgt.setText("TARGET" + ("  ●" if slot == "target" else ""))

    def show_aircraft(self, defn: AircraftDefinition) -> None:
        self.name.setText(defn.name)
        self.klass.setText(defn.class_label)
        demo = "  ·  demo parameters" if defn.demo_flight.is_demo else ""
        self.stats.setText(
            f"Mass         {defn.demo_flight.mass_kg:.1f} kg{demo}\n"
            f"Cruise       {defn.demo_flight.cruise_speed_mps:.0f} m/s\n"
            f"Stall        {defn.demo_flight.stall_speed_mps:.0f} m/s\n"
            f"Max          {defn.demo_flight.max_speed_mps:.0f} m/s\n"
            f"Class        {defn.class_label}"
        )
        bits = []
        if defn.unconfigured:
            bits.append("UNCONFIGURED MODEL")
        if not defn.playable_ego:
            bits.append("NOT A PLAYABLE EGO — generic fixed-wing profile")
        if defn.meta.source == "models":
            bits.append("User GLB")
        self.warn.setText("  ·  ".join(bits))
