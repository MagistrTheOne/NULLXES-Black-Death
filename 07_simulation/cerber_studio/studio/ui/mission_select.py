"""Demo mission picker — not ArduPlane protocol."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QPushButton, QVBoxLayout, QWidget

from ..config.settings import UserSettings
from ..missions.registry import MissionDefinition
from .theme import scale_px


class MissionSelectView(QWidget):
    selected = Signal()
    back = Signal()

    def __init__(self, settings: UserSettings, parent=None) -> None:
        super().__init__(parent)
        self.settings = settings
        self.missions: list[MissionDefinition] = []
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        root = QHBoxLayout(self)
        root.setContentsMargins(56, 48, 56, 48)
        left = QVBoxLayout()
        head = QHBoxLayout()
        self.heading = QLabel("MISSION")
        self.heading.setObjectName("Title")
        self.back_btn = QPushButton("BACK")
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
        self.desc = QLabel("")
        self.desc.setObjectName("Muted")
        self.desc.setWordWrap(True)
        self.note = QLabel("Demo mission. Not ArduPlane Mission Protocol.")
        self.note.setObjectName("Muted")
        self.btn = QPushButton("START MISSION")
        self.btn.setObjectName("PrimaryBtn")
        self.btn.clicked.connect(self.selected.emit)
        right.addWidget(self.name)
        right.addWidget(self.meta)
        right.addSpacing(12)
        right.addWidget(self.desc)
        right.addStretch(1)
        right.addWidget(self.note)
        right.addWidget(self.btn, 0, Qt.AlignLeft)
        root.addLayout(right, 1)
        self.relayout()

    def relayout(self) -> None:
        s = self.settings
        self.heading.setStyleSheet(f"font-size:{scale_px(self, s, 22)}px; letter-spacing:4px;")
        self.name.setStyleSheet(f"font-size:{scale_px(self, s, 28)}px;")
        self.meta.setStyleSheet(f"font-size:{scale_px(self, s, 13)}px;")
        self.desc.setStyleSheet(f"font-size:{scale_px(self, s, 14)}px;")

    def set_missions(self, items: list[MissionDefinition], current_id: str) -> None:
        self.missions = items
        self.list.clear()
        idx = 0
        for i, m in enumerate(items):
            self.list.addItem(QListWidgetItem(m.name))
            if m.id == current_id:
                idx = i
        if items:
            self.list.setCurrentRow(idx)

    def current(self) -> MissionDefinition | None:
        row = self.list.currentRow()
        if 0 <= row < len(self.missions):
            return self.missions[row]
        return None

    def _on_row(self, row: int) -> None:
        if not (0 <= row < len(self.missions)):
            return
        m = self.missions[row]
        dur = "Open" if m.duration_s <= 0 else f"{m.duration_s}s"
        tgt = "Yes" if m.target else "No"
        self.name.setText(m.name)
        self.meta.setText(
            f"Type          {m.type.replace('_', ' ').upper()}\n"
            f"Environment   {m.environment.upper()}\n"
            f"Target        {tgt}\n"
            f"Duration      {dur}"
        )
        self.desc.setText(m.description)
