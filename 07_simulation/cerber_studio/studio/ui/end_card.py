"""End-of-flight card + replay entry."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget

from ..config.settings import UserSettings
from ..i18n import t
from .theme import scale_px


class EndCardView(QWidget):
    replay = Signal()
    flight_path = Signal()
    events = Signal()
    cerber = Signal()
    statistics = Signal()
    hangar = Signal()

    def __init__(self, settings: UserSettings, parent=None) -> None:
        super().__init__(parent)
        self.cfg = settings
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(80, 80, 80, 80)
        lay.addStretch(1)
        self.title = QLabel("FLIGHT COMPLETE")
        self.title.setObjectName("Title")
        self.stats = QLabel("")
        self.stats.setObjectName("Muted")
        lay.addWidget(self.title)
        lay.addWidget(self.stats)
        lay.addSpacing(20)
        self.buttons = []
        self._keys = ("replay", "flight_path", "events", "cerber", "statistics", "aircraft")
        for key, sig in (
            ("replay", self.replay),
            ("flight_path", self.flight_path),
            ("events", self.events),
            ("cerber", self.cerber),
            ("statistics", self.statistics),
            ("aircraft", self.hangar),
        ):
            b = QPushButton(t(key))
            b.setObjectName("MenuBtn")
            b.setCursor(Qt.PointingHandCursor)
            b.clicked.connect(sig.emit)
            lay.addWidget(b)
            self.buttons.append(b)
        lay.addStretch(2)
        self.retranslate()
        self.relayout()

    def set_summary(
        self,
        time_s: float,
        km: float,
        max_alt: float,
        max_spd: float,
        grade: str,
        cert: dict | None = None,
        op_name: str = "",
    ) -> None:
        h = int(time_s // 3600)
        m = int((time_s % 3600) // 60)
        sec = int(time_s % 60)
        clock = f"{h:02d}:{m:02d}:{sec:02d}"
        land = f"LANDING {grade}" if grade else ""
        lines = [
            f"{clock}     {km:.1f} km",
            f"MAX ALT  {max_alt:.0f} m     MAX SPEED  {max_spd:.0f} m/s",
            land,
        ]
        if cert:
            name = op_name or "CHALLENGE"
            self.title.setText(f"{name}\nCOMPLETE")
            vz = cert.get("touchdown_ms")
            vz_txt = f"{vz:.1f} m/s" if isinstance(vz, (int, float)) else "—"
            lines.extend(
                [
                    "",
                    f"APPROACH        {cert.get('approach', '—')}",
                    f"TOUCHDOWN       {vz_txt}",
                    f"ASSIST          {cert.get('assist', '—')}",
                    "",
                    "CERTIFIED",
                ]
            )
        else:
            self.title.setText(t("flight_complete"))
        self.stats.setText("\n".join(lines))

    def retranslate(self) -> None:
        self.title.setText(t("flight_complete"))
        for key, b in zip(self._keys, self.buttons):
            b.setText(t(key))

    def relayout(self) -> None:
        s = self.cfg
        self.title.setStyleSheet(f"font-size:{scale_px(self, s, 32)}px; letter-spacing:6px;")
        self.stats.setStyleSheet(f"font-size:{scale_px(self, s, 16)}px;")
        w = scale_px(self, s, 320)
        for b in self.buttons:
            b.setFixedWidth(w)
