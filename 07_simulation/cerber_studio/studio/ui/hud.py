"""Product HUD — aerospace, readable at 1080p. Not a game overlay."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

from ..config.settings import HudSettings, UserSettings, apply_hud_preset
from .theme import scale_px


def compass_tape(hdg: float) -> str:
    h = hdg % 360.0
    names = ((0, "N"), (45, "NE"), (90, "E"), (135, "SE"), (180, "S"), (225, "SW"), (270, "W"), (315, "NW"), (360, "N"))
    best = min(names, key=lambda c: min(abs(c[0] - h), 360.0 - abs(c[0] - h)))
    return f"HDG {h:03.0f}  {best[1]}"


def _thr_bar(thr: float) -> str:
    n = max(0, min(20, int(round(thr * 20))))
    return "█" * n + "░" * (20 - n)


class ProductHud(QWidget):
    def __init__(self, settings: UserSettings, parent=None) -> None:
        super().__init__(parent)
        self.settings = settings
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        root = QVBoxLayout(self)
        root.setContentsMargins(48, 36, 48, 36)

        top = QHBoxLayout()
        self.mode = QLabel("MANUAL")
        self.mode.setObjectName("Title")
        self.phase = QLabel("")
        self.phase.setObjectName("Muted")
        self.cerber = QLabel("CERBER  ·")
        self.cerber.setObjectName("Muted")
        self.fps = QLabel("")
        self.fps.setObjectName("Muted")
        top.addWidget(self.mode)
        top.addSpacing(20)
        top.addWidget(self.phase)
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
        self.bar = QLabel("")
        for lab in (self.alt, self.spd, self.thr, self.bar):
            lab.setObjectName("Title")
            mid.addWidget(lab)
        self.cue = QLabel("")
        self.cue.setObjectName("Muted")
        self.inst = QLabel("")
        self.inst.setObjectName("Muted")
        mid.addSpacing(8)
        mid.addWidget(self.cue)
        mid.addWidget(self.inst)
        root.addLayout(mid)
        root.addStretch(1)

        bot = QHBoxLayout()
        left = QVBoxLayout()
        self.target = QLabel("")
        self.mission = QLabel("")
        self.hint = QLabel("")
        self.debug = QLabel("")
        self.target.setObjectName("Muted")
        self.mission.setObjectName("Muted")
        self.hint.setObjectName("Muted")
        self.debug.setObjectName("Muted")
        left.addWidget(self.target)
        left.addWidget(self.mission)
        left.addWidget(self.hint)
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
        self.mode.setStyleSheet(f"font-size:{scale_px(self, s, 22)}px; letter-spacing:3px;")
        self.phase.setStyleSheet(f"font-size:{scale_px(self, s, 16)}px; letter-spacing:2px;")
        self.cerber.setStyleSheet(f"font-size:{scale_px(self, s, 14)}px;")
        self.fps.setStyleSheet(f"font-size:{scale_px(self, s, 13)}px;")
        for lab in (self.alt, self.spd, self.thr):
            lab.setStyleSheet(f"font-size:{scale_px(self, s, 28)}px;")
        self.bar.setStyleSheet(f"font-size:{scale_px(self, s, 14)}px; letter-spacing:1px;")
        self.cue.setStyleSheet(f"font-size:{scale_px(self, s, 16)}px; letter-spacing:2px;")
        self.inst.setStyleSheet(f"font-size:{scale_px(self, s, 15)}px; letter-spacing:2px;")
        self.hint.setStyleSheet(f"font-size:{scale_px(self, s, 14)}px;")
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
        phase: str = "",
        cue: str = "",
        training: str = "",
        hint: str = "",
        hdg: float = 0.0,
        vs: float = 0.0,
        dist: float | None = None,
        wind: str = "",
        clock: str = "",
        layer: str = "flight",
        compass: str = "",
    ) -> None:
        h: HudSettings = self.settings.hud
        layer = (layer or h.layer or h.preset or "flight").lower()
        if not h.hud or layer == "clean":
            if layer == "clean":
                self.show()
                self.mode.setText("")
                self.phase.setText("")
                self.cerber.setText("")
                self.fps.setText("")
                self.alt.setText("")
                self.spd.setText("")
                self.thr.setText("")
                self.bar.setText("")
                self.cue.setText("")
                self.inst.setText("")
                self.target.setText("")
                self.mission.setText("")
                self.hint.setText("")
                self.debug.setText("")
                self.reticle.hide()
                return
            self.hide()
            return
        self.show()
        label = "FOLLOW" if mode == "PURSUIT" else mode
        self.mode.setText(f"{layer.upper()}  {label}" if h.mode else "")
        self.mode.setVisible(h.mode)
        self.phase.setText(phase)
        if layer == "operator":
            if cerber_ok is None:
                self.cerber.setText("CERBER  ·")
            elif cerber_ok:
                self.cerber.setText("CERBER  ●")
            else:
                self.cerber.setText("CERBER  ○")
        else:
            self.cerber.setText("")
        self.fps.setText(f"{fps:.0f} FPS" if h.fps or layer == "engineering" else "")
        show_inst = layer in ("flight", "operator", "engineering")
        self.alt.setText(f"ALT   {alt:.0f} m" if show_inst and h.altitude else "")
        self.spd.setText(f"IAS    {spd:.0f} m/s" if show_inst and h.speed else "")
        self.thr.setText(f"THR    {thr * 100:.0f}%" if show_inst and h.throttle else "")
        self.bar.setText(_thr_bar(thr) if show_inst and h.throttle else "")
        self.cue.setText(cue)
        tape = compass or f"HDG {hdg:03.0f}"
        vs_txt = f"V/S {vs:+.1f}"
        dist_txt = f"DIST {dist:.0f} m" if dist is not None else ""
        self.inst.setText(f"{tape}     {vs_txt}     {wind}     {clock}     {dist_txt}".strip() if show_inst else "")
        self.reticle.setVisible(h.reticle and not h.minimal and layer != "flight")
        if layer == "flight":
            self.target.setText("")
            self.mission.setText(training or "")
            self.hint.setText("")
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
        mission_txt = training or mission_name
        self.mission.setText(mission_txt if h.mission_path else "")
        self.hint.setText(hint)
        self.debug.setText(debug if h.debug_labels or layer == "engineering" else "")
