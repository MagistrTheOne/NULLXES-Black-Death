"""NOW PLAYING + FLIGHT MIX controls. pygame mixer backend unchanged."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QSlider, QVBoxLayout, QWidget

from ..config.settings import UserSettings
from ..i18n import t
from .theme import scale_px


class NowPlayingBar(QWidget):
    prev_track = Signal()
    play_pause = Signal()
    next_track = Signal()
    seek = Signal(float)
    shuffle = Signal()

    def __init__(self, settings: UserSettings, parent=None) -> None:
        super().__init__(parent)
        self.settings = settings
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, False)
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 8, 16, 8)
        self.title = QLabel("")
        self.title.setObjectName("Muted")
        root.addWidget(self.title)
        self.seek_bar = QSlider(Qt.Horizontal)
        self.seek_bar.setRange(0, 1000)
        self.seek_bar.sliderReleased.connect(self._seek)
        root.addWidget(self.seek_bar)
        row = QHBoxLayout()
        self.btn_prev = QPushButton("⏮")
        self.btn_play = QPushButton("▶")
        self.btn_next = QPushButton("⏭")
        self.btn_shuf = QPushButton("SHUF")
        for b, sig in (
            (self.btn_prev, self.prev_track),
            (self.btn_play, self.play_pause),
            (self.btn_next, self.next_track),
            (self.btn_shuf, self.shuffle),
        ):
            b.setObjectName("GhostBtn")
            b.clicked.connect(sig.emit)
            row.addWidget(b)
        row.addStretch(1)
        root.addLayout(row)
        self._paused = False
        self.relayout()

    def _seek(self) -> None:
        self.seek.emit(self.seek_bar.value() / 1000.0)

    def set_track(self, name: str, paused: bool = False, pos: float = 0.0) -> None:
        self._paused = paused
        self.title.setText(f"{t('now_playing')}   {name or '—'}")
        self.btn_play.setText("▶" if paused else "⏸")
        self.seek_bar.blockSignals(True)
        self.seek_bar.setValue(int(max(0.0, min(1.0, pos)) * 1000))
        self.seek_bar.blockSignals(False)

    def relayout(self) -> None:
        s = self.settings
        self.title.setStyleSheet(f"font-size:{scale_px(self, s, 13)}px; letter-spacing:2px;")
