"""Pilot record / clearance card."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget

from ..config.settings import UserSettings
from ..i18n import t
from ..pilot import PilotRecord
from .theme import scale_px


class PilotRecordView(QWidget):
    back = Signal()

    def __init__(self, settings: UserSettings, parent=None) -> None:
        super().__init__(parent)
        self.cfg = settings
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(80, 80, 80, 80)
        self.heading = QLabel("")
        self.heading.setObjectName("Title")
        self.body = QLabel("")
        self.body.setObjectName("Muted")
        self.back_btn = QPushButton("")
        self.back_btn.setObjectName("GhostBtn")
        self.back_btn.clicked.connect(self.back.emit)
        lay.addWidget(self.heading)
        lay.addSpacing(16)
        lay.addWidget(self.body)
        lay.addStretch(1)
        lay.addWidget(self.back_btn, 0, Qt.AlignLeft)
        self.retranslate()
        self.relayout()

    def show_record(self, rec: PilotRecord) -> None:
        hours = rec.time_s / 3600.0
        km = rec.distance_m / 1000.0
        night = t("unlocked") if rec.night_unlocked else t("locked")
        discovered = "\n".join(rec.discovered) if rec.discovered else "—"
        certs = "\n".join(c.get("name", "") for c in rec.certs if isinstance(c, dict)) if rec.certs else "—"
        self.body.setText(
            f"{t('flights')}     {rec.flights}\n"
            f"{t('time')}        {hours:.1f} h\n"
            f"{t('distance')}    {km:.1f} km\n"
            f"LEVEL      {rec.level}\n"
            f"NIGHT      {night}\n"
            f"LANDING    {rec.last_grade or '—'}\n\n"
            f"{t('discovered')}\n{discovered}\n\n"
            f"{t('certified')}\n{certs}"
        )

    def retranslate(self) -> None:
        self.heading.setText(t("pilot_record"))
        self.back_btn.setText(t("back"))

    def relayout(self) -> None:
        s = self.cfg
        self.heading.setStyleSheet(f"font-size:{scale_px(self, s, 28)}px; letter-spacing:4px;")
        self.body.setStyleSheet(f"font-size:{scale_px(self, s, 16)}px;")
