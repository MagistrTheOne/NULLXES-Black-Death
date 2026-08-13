"""Demo mission picker — not ArduPlane protocol."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QPushButton, QVBoxLayout, QWidget

from ..config.settings import UserSettings
from ..i18n import t
from ..missions.registry import MissionDefinition
from .theme import scale_px


def _mission_name(m: MissionDefinition) -> str:
    key = f"mission_{m.id}"
    label = t(key)
    return label if label != key else m.name


def _mission_desc(m: MissionDefinition) -> str:
    key = f"mission_desc_{m.id}"
    label = t(key)
    return label if label != key else m.description


class MissionSelectView(QWidget):
    selected = Signal()
    back = Signal()

    def __init__(self, settings: UserSettings, parent=None) -> None:
        super().__init__(parent)
        self.settings = settings
        self.missions: list[MissionDefinition] = []
        self._current_id = ""
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
        self.desc = QLabel("")
        self.desc.setObjectName("Muted")
        self.desc.setWordWrap(True)
        self.note = QLabel("")
        self.note.setObjectName("Muted")
        self.btn = QPushButton("")
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
        self.retranslate()
        self.relayout()

    def retranslate(self) -> None:
        self.heading.setText(t("mission"))
        self.back_btn.setText(t("back"))
        self.btn.setText(t("start_mission"))
        self.note.setText(t("demo_mission"))
        if self.missions:
            self.set_missions(self.missions, self._current_id)

    def relayout(self) -> None:
        s = self.settings
        self.heading.setStyleSheet(f"font-size:{scale_px(self, s, 22)}px; letter-spacing:4px;")
        self.name.setStyleSheet(f"font-size:{scale_px(self, s, 28)}px;")
        self.meta.setStyleSheet(f"font-size:{scale_px(self, s, 13)}px;")
        self.desc.setStyleSheet(f"font-size:{scale_px(self, s, 14)}px;")

    def set_missions(self, items: list[MissionDefinition], current_id: str) -> None:
        self.missions = items
        self._current_id = current_id
        self.list.blockSignals(True)
        self.list.clear()
        idx = 0
        for i, m in enumerate(items):
            self.list.addItem(QListWidgetItem(_mission_name(m)))
            if m.id == current_id:
                idx = i
        self.list.blockSignals(False)
        if items:
            self.list.setCurrentRow(idx)
            self._on_row(idx)

    def current(self) -> MissionDefinition | None:
        row = self.list.currentRow()
        if 0 <= row < len(self.missions):
            return self.missions[row]
        return None

    def _on_row(self, row: int) -> None:
        if not (0 <= row < len(self.missions)):
            return
        m = self.missions[row]
        self._current_id = m.id
        dur = t("open") if m.duration_s <= 0 else f"{m.duration_s}s"
        tgt = t("yes") if m.target else t("no")
        self.name.setText(_mission_name(m))
        self.meta.setText(
            f"{t('type')}          {m.type.replace('_', ' ').upper()}\n"
            f"{t('environment')}   {m.environment.upper()}\n"
            f"{t('target')}        {tgt}\n"
            f"{t('duration')}      {dur}"
        )
        self.desc.setText(_mission_desc(m))
