"""Product HUD — not a debug terminal."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

from ..config.settings import HudSettings, UserSettings, apply_hud_preset
from .theme import scale_px


class ProductHud(QWidget):
    def __init__(self, settings: UserSettings, parent=None) -> None:
        super().__init__(parent)
        self.settings = settings
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        root = QVBoxLayout(self)
        root.setContentsMargins(36, 28, 36, 28)

        top = QHBoxLayout()
        self.mode = QLabel("MANUAL")
        self.mode.setObjectName("Title")
        self.cerber = QLabel("CERBER  ·")
        self.cerber.setObjectName("Muted")
        self.fps = QLabel("")
        self.fps.setObjectName("Muted")
        top.addWidget(self.mode)
        top.addStretch(1)
        top.addWidget(self.fps)
        top.addSpacing(16)
        top.addWidget(self.cerber)
        root.addLayout(top)
        root.addStretch(1)

        mid = QVBoxLayout()
        self.alt = QLabel("")
        self.spd = QLabel("")
        self.thr = QLabel("")
        for lab in (self.alt, self.spd, self.thr):
            lab.setObjectName("Title")
            mid.addWidget(lab)
        root.addLayout(mid)
        root.addStretch(1)

        bot = QHBoxLayout()
        left = QVBoxLayout()
        self.target = QLabel("")
        self.mission = QLabel("")
        self.debug = QLabel("")
        self.target.setObjectName("Muted")
        self.mission.setObjectName("Muted")
        self.debug.setObjectName("Muted")
        left.addWidget(self.target)
        left.addWidget(self.mission)
        left.addWidget(self.debug)
        bot.addLayout(left)
        bot.addStretch(1)
        self.reticle = QLabel("·")
        self.reticle.setAlignment(Qt.AlignCenter)
        bot.addWidget(self.reticle)
        bot.addStretch(1)
        root.addLayout(bot)
        self.relayout()

    def relayout(self) -> None:
        s = self.settings
        self.mode.setStyleSheet(f"font-size:{scale_px(self, s, 16)}px; letter-spacing:3px;")
        self.cerber.setStyleSheet(f"font-size:{scale_px(self, s, 13)}px;")
        self.fps.setStyleSheet(f"font-size:{scale_px(self, s, 12)}px;")
        for lab in (self.alt, self.spd, self.thr):
            lab.setStyleSheet(f"font-size:{scale_px(self, s, 18)}px;")
        self.reticle.setStyleSheet(f"font-size:{scale_px(self, s, 22)}px; color:#F2F2F2;")

    def apply_preset(self, name: str) -> None:
        apply_hud_preset(self.settings.hud, name, overwrite=True)
        self.settings.save()

    def update_hud(
        self,
        *,
        mode: str,
        alt: float,
        spd: float,
        thr: float,
        cerber_ok: bool | None,
        cerber_detail: str,
        fps: float,
        target_name: str,
        target_dist: float | None,
        track_id: int | None,
        mission_name: str,
        debug: str,
    ) -> None:
        h: HudSettings = self.settings.hud
        if not h.hud:
            self.hide()
            return
        self.show()
        label = "FOLLOW" if mode == "PURSUIT" else mode
        self.mode.setText(label if h.mode else "")
        self.mode.setVisible(h.mode)
        if cerber_ok is None:
            self.cerber.setText("CERBER  ·")
        elif cerber_ok:
            self.cerber.setText("CERBER  ●")
        else:
            self.cerber.setText("CERBER  ○")
        self.fps.setText(f"{fps:.0f} FPS" if h.fps else "")
        self.alt.setText(f"ALT  {alt:.0f} m" if h.altitude and h.telemetry else "")
        self.spd.setText(f"SPD  {spd:.0f} m/s" if h.speed and h.telemetry else "")
        self.thr.setText(f"THR  {thr * 100:.0f}%" if h.throttle and h.telemetry else "")
        self.reticle.setVisible(h.reticle and not h.minimal)
        if h.minimal:
            self.target.setText("")
            self.mission.setText("")
            self.debug.setText("")
            return
        t_lines = []
        if target_name:
            t_lines.append(f"TARGET\n{target_name}")
            if track_id is not None and h.cerber_tracks:
                t_lines.append(f"TRACK {track_id:02d}")
            if target_dist is not None:
                t_lines.append(f"DIST  {target_dist:.0f} m")
        self.target.setText("\n".join(t_lines))
        self.mission.setText(f"MISSION\n{mission_name}" if h.mission_path else "")
        self.debug.setText(debug if h.debug_labels else "")
        if not h.target_boxes:
            pass
