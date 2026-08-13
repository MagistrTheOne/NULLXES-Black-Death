"""Replay timeline — events as jump points. Not TRACE_SPEC."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QPushButton, QSlider, QVBoxLayout, QWidget

from ..config.settings import UserSettings
from .theme import scale_px


class ReplayTimeline(QWidget):
    seek = Signal(int)
    close = Signal()

    def __init__(self, settings: UserSettings, parent=None) -> None:
        super().__init__(parent)
        self.cfg = settings
        self.poses: list[dict] = []
        self.events: list[dict] = []
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        root = QVBoxLayout(self)
        root.setContentsMargins(40, 28, 40, 28)
        head = QHBoxLayout()
        self.title = QLabel("BLACKBOX REPLAY")
        self.title.setObjectName("Title")
        self.back = QPushButton("BACK")
        self.back.setObjectName("GhostBtn")
        self.back.clicked.connect(self.close.emit)
        head.addWidget(self.title)
        head.addStretch(1)
        head.addWidget(self.back)
        root.addLayout(head)
        self.clock = QLabel("00:00")
        self.clock.setObjectName("Muted")
        root.addWidget(self.clock)
        self.slider = QSlider(Qt.Horizontal)
        self.slider.valueChanged.connect(self.seek.emit)
        root.addWidget(self.slider)
        self.list = QListWidget()
        self.list.currentRowChanged.connect(self._jump_event)
        root.addWidget(self.list, 1)
        self.relayout()

    def set_data(self, poses: list[dict], events: list[dict]) -> None:
        self.poses = poses
        self.events = events
        self.slider.setRange(0, max(0, len(poses) - 1))
        self.list.clear()
        for ev in events:
            t = float(ev.get("t") or 0.0)
            kind = str(ev.get("kind") or "")
            QListWidgetItem(f"{int(t // 60):02d}:{int(t % 60):02d}    {kind}", self.list)

    def set_index(self, i: int) -> None:
        self.slider.blockSignals(True)
        self.slider.setValue(i)
        self.slider.blockSignals(False)
        if 0 <= i < len(self.poses):
            t = float(self.poses[i].get("t") or 0.0)
            self.clock.setText(f"{int(t // 60):02d}:{int(t % 60):02d}  /  {len(self.poses)} frames")

    def _jump_event(self, row: int) -> None:
        if not (0 <= row < len(self.events)) or not self.poses:
            return
        t = float(self.events[row].get("t") or 0.0)
        best = min(range(len(self.poses)), key=lambda i: abs(float(self.poses[i].get("t") or 0.0) - t))
        self.seek.emit(best)

    def relayout(self) -> None:
        s = self.cfg
        self.title.setStyleSheet(f"font-size:{scale_px(self, s, 22)}px; letter-spacing:4px;")
