"""Product settings. Only controls that bind to real runtime."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSlider,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from ..audio.playlist import AUDIO_EXTS, SLOT_COUNT, scan_playlist
from ..config.settings import (
    DEFAULT_BINDINGS,
    FOV_VALUES,
    UI_SCALES,
    UserSettings,
    apply_graphics_preset,
    apply_hud_preset,
)
from ..display import supported_resolutions
from ..i18n import lang, t
from .theme import scale_px

CAT_KEYS = (
    "cat_display",
    "cat_graphics",
    "cat_audio",
    "cat_controls",
    "cat_hud",
    "cat_simulation",
    "cat_system",
)


def _combo(items: list[str], current: str) -> QComboBox:
    box = QComboBox()
    box.addItems(items)
    idx = box.findText(current)
    if idx >= 0:
        box.setCurrentIndex(idx)
    return box


def _slider(value: int) -> QSlider:
    sl = QSlider(Qt.Horizontal)
    sl.setRange(0, 100)
    sl.setValue(int(value))
    return sl


class SettingsView(QWidget):
    closed = Signal()
    applied = Signal()
    reset_settings = Signal()
    reset_window = Signal()
    open_logs = Signal()
    language = Signal(str)
    tracks_dropped = Signal(list)

    def __init__(self, settings: UserSettings, parent=None) -> None:
        super().__init__(parent)
        self.settings = settings
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAcceptDrops(True)
        root = QVBoxLayout(self)
        root.setContentsMargins(48, 36, 48, 36)
        head = QHBoxLayout()
        self.heading = QLabel("")
        self.heading.setObjectName("Title")
        self.back = QPushButton("")
        self.back.setObjectName("GhostBtn")
        self.back.clicked.connect(self._on_back)
        head.addWidget(self.heading)
        head.addStretch(1)
        head.addWidget(self.back)
        root.addLayout(head)

        body = QHBoxLayout()
        self.nav = QListWidget()
        for key in CAT_KEYS:
            self.nav.addItem(QListWidgetItem(t(key)))
        self.pages = QStackedWidget()
        self.nav.currentRowChanged.connect(self.pages.setCurrentIndex)
        body.addWidget(self.nav, 0)
        body.addWidget(self.pages, 1)
        root.addLayout(body, 1)

        self._build_display()
        self._build_graphics()
        self._build_audio()
        self._build_controls()
        self._build_hud()
        self._build_sim()
        self._build_system()
        self.nav.setCurrentRow(0)
        self.retranslate()
        self.relayout()

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if self._audio_urls(event.mimeData()):
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent) -> None:
        paths = self._audio_urls(event.mimeData())
        if paths:
            self.tracks_dropped.emit(paths)
            event.acceptProposedAction()

    def _audio_urls(self, mime) -> list[str]:
        if mime is None or not mime.hasUrls():
            return []
        out: list[str] = []
        for url in mime.urls():
            path = Path(url.toLocalFile())
            if path.suffix.lower() in AUDIO_EXTS and path.is_file():
                out.append(str(path))
        return out

    def retranslate(self) -> None:
        self.heading.setText(t("settings"))
        self.back.setText(t("back"))
        for i, key in enumerate(CAT_KEYS):
            item = self.nav.item(i)
            if item is not None:
                item.setText(t(key))
        self.mute.setText(t("mute_all"))
        self.slot_label.setText(t("music_slots"))
        self.lang_lab.setText(t("language"))
        self.launch_assist.setText(t("launch_assist"))
        self.refresh_playlist()
        self._sync_lang_box()

    def relayout(self) -> None:
        s = self.settings
        self.heading.setStyleSheet(f"font-size:{scale_px(self, s, 22)}px; letter-spacing:4px;")
        self.nav.setFixedWidth(scale_px(self, s, 220))

    def _on_back(self) -> None:
        self.collect()
        self.settings.save()
        self.applied.emit()
        self.closed.emit()

    def _build_display(self) -> None:
        w = QWidget()
        w.setObjectName("GlassPanel")
        f = QFormLayout(w)
        d = self.settings.display
        self.mode = _combo(["fullscreen", "borderless", "windowed"], d.mode)
        modes = supported_resolutions()
        labels = [f"{a}×{b}" for a, b in modes]
        current = f"{d.resolution[0]}×{d.resolution[1]}"
        self.res = _combo(labels, current if current in labels else labels[-1])
        self._res_values = modes
        self.vsync = QCheckBox("ON")
        self.vsync.setChecked(d.vsync)
        fps_items = ["30", "60", "120", "144", "Unlimited"]
        fps_cur = "Unlimited" if d.fps_limit == 0 else str(d.fps_limit)
        self.fps = _combo(fps_items, fps_cur)
        self.ui_scale = _combo([x if x == "auto" else f"{x}%" for x in UI_SCALES], "auto" if d.ui_scale == "auto" else f"{d.ui_scale}%")
        self.fov = _combo([str(v) for v in FOV_VALUES], str(d.fov))
        f.addRow("Display Mode", self.mode)
        f.addRow("Resolution", self.res)
        f.addRow("VSync", self.vsync)
        f.addRow("FPS Limit", self.fps)
        f.addRow("UI Scale", self.ui_scale)
        f.addRow("Field of View", self.fov)
        note = QLabel("Resolution drives the render buffer. Borderless/Fullscreen fill the monitor.")
        note.setObjectName("Muted")
        note.setWordWrap(True)
        f.addRow(note)
        self.pages.addWidget(w)

    def _build_graphics(self) -> None:
        w = QWidget()
        f = QFormLayout(w)
        g = self.settings.graphics
        self.gfx_preset = _combo(["low", "medium", "high", "ultra"], g.preset)
        self.gfx_preset.currentTextChanged.connect(self._on_gfx_preset)
        self.render_scale = QSlider(Qt.Horizontal)
        self.render_scale.setRange(50, 150)
        self.render_scale.setValue(int(g.render_scale * 100))
        self.rs_label = QLabel(f"{int(g.render_scale * 100)}%")
        rs_row = QHBoxLayout()
        rs_row.addWidget(self.render_scale)
        rs_row.addWidget(self.rs_label)
        self.render_scale.valueChanged.connect(lambda v: self.rs_label.setText(f"{v}%"))
        aa = {0: "OFF", 2: "MSAA 2×", 4: "MSAA 4×", 8: "MSAA 8×"}
        self.msaa = _combo(list(aa.values()), aa.get(g.msaa, "MSAA 4×"))
        self.tex = _combo(["low", "medium", "high"], g.texture_quality)
        self.view = _combo(["low", "medium", "high"], g.view_distance)
        f.addRow("Graphics Preset", self.gfx_preset)
        wrap = QWidget()
        wrap.setLayout(rs_row)
        f.addRow("Render Scale", wrap)
        f.addRow("Anti-Aliasing", self.msaa)
        f.addRow("Texture Quality", self.tex)
        f.addRow("View Distance", self.view)
        note = QLabel("MSAA applies on next launch. View distance drives fog and far clip. Terrain LOD follows the aircraft.")
        note.setObjectName("Muted")
        note.setWordWrap(True)
        f.addRow(note)
        self.pages.addWidget(w)

    def _on_gfx_preset(self, name: str) -> None:
        apply_graphics_preset(self.settings.graphics, name)
        g = self.settings.graphics
        self.render_scale.setValue(int(g.render_scale * 100))
        aa = {0: "OFF", 2: "MSAA 2×", 4: "MSAA 4×", 8: "MSAA 8×"}
        self.msaa.setCurrentText(aa.get(g.msaa, "MSAA 4×"))
        self.tex.setCurrentText(g.texture_quality)
        self.view.setCurrentText(g.view_distance)

    def _build_audio(self) -> None:
        w = QWidget()
        f = QFormLayout(w)
        a = self.settings.audio
        self.mute = QCheckBox("")
        self.mute.setChecked(a.muted)
        self.vol_master = _slider(int(a.master * 100))
        self.vol_music = _slider(int(getattr(a, "music", 0.75) * 100))
        self.vol_engine = _slider(int(a.engine * 100))
        self.vol_wind = _slider(int(a.wind * 100))
        self.vol_env = _slider(int(a.environment * 100))
        self.vol_ui = _slider(int(a.ui * 100))
        self.vol_warn = _slider(int(a.warning * 100))
        self.slot_label = QLabel("")
        self.playlist = QListWidget()
        self.playlist.setMinimumHeight(180)
        f.addRow(self.mute)
        f.addRow("Master", self.vol_master)
        f.addRow("Music", self.vol_music)
        f.addRow("Engine / Propeller", self.vol_engine)
        f.addRow("Wind", self.vol_wind)
        f.addRow("Environment / Storm", self.vol_env)
        f.addRow("UI", self.vol_ui)
        f.addRow("Warning", self.vol_warn)
        f.addRow(self.slot_label)
        f.addRow(self.playlist)
        note = QLabel("")
        note.setObjectName("Muted")
        note.setWordWrap(True)
        self.audio_note = note
        f.addRow(note)
        self.pages.addWidget(w)

    def refresh_playlist(self) -> None:
        tracks = scan_playlist()
        self.playlist.clear()
        n = max(SLOT_COUNT, len(tracks) + 1)
        for i in range(n):
            if i < len(tracks):
                self.playlist.addItem(QListWidgetItem(f"{i + 1:02d}  {tracks[i].stem}"))
            else:
                self.playlist.addItem(QListWidgetItem(f"{i + 1:02d}  {t('empty_slot')}"))
        self.audio_note.setText(t("drop_music"))

    def _build_controls(self) -> None:
        w = QWidget()
        f = QFormLayout(w)
        c = self.settings.controls
        self.sens = QSlider(Qt.Horizontal)
        self.sens.setRange(20, 200)
        self.sens.setValue(int(c.sensitivity * 100))
        self.cam_sens = QSlider(Qt.Horizontal)
        self.cam_sens.setRange(20, 200)
        self.cam_sens.setValue(int(c.camera_sensitivity * 100))
        self.invert = QCheckBox("Invert Y")
        self.invert.setChecked(c.invert_y)
        f.addRow("Mouse / command sensitivity", self.sens)
        f.addRow("Camera sensitivity", self.cam_sens)
        f.addRow(self.invert)
        binds = dict(DEFAULT_BINDINGS)
        binds.update(c.bindings or {})
        labels = [
            ("Pitch Up", "pitch_up"),
            ("Pitch Down", "pitch_down"),
            ("Roll Left", "roll_left"),
            ("Roll Right", "roll_right"),
            ("Yaw Left", "yaw_left"),
            ("Yaw Right", "yaw_right"),
            ("Throttle Up", "throttle_up"),
            ("Throttle Down", "throttle_down"),
            ("Launch", "launch"),
            ("Reset", "reset"),
            ("Mode Manual", "mode_manual"),
            ("Mode Assist", "mode_assist"),
            ("Mode Follow", "mode_follow"),
            ("Mode Mission", "mode_mission"),
            ("Pause", "pause"),
        ]
        for title, key in labels:
            lab = QLabel(binds.get(key, "—"))
            f.addRow(title, lab)
        note = QLabel("Keyboard + mouse. Gamepad is not wired.")
        note.setObjectName("Muted")
        f.addRow(note)
        self.pages.addWidget(w)

    def _build_hud(self) -> None:
        w = QWidget()
        f = QFormLayout(w)
        h = self.settings.hud
        self.hud_preset = _combo(["clean", "operator", "engineering"], h.preset)
        self.hud_preset.currentTextChanged.connect(lambda n: apply_hud_preset(self.settings.hud, n, overwrite=True) or self._sync_hud_checks())
        self.chk: dict[str, QCheckBox] = {}
        for key, title in (
            ("hud", "HUD"),
            ("minimal", "Minimal HUD"),
            ("fps", "FPS"),
            ("telemetry", "Telemetry"),
            ("cerber_tracks", "CERBER Tracks"),
            ("target_boxes", "Target Boxes"),
            ("mission_path", "Mission Path"),
            ("debug_labels", "Debug Labels"),
            ("reticle", "Reticle"),
            ("flight_vector", "Flight Vector"),
            ("altitude", "Altitude"),
            ("speed", "Speed"),
            ("throttle", "Throttle"),
            ("mode", "Mode"),
        ):
            box = QCheckBox(title)
            box.setChecked(bool(getattr(h, key)))
            self.chk[key] = box
            f.addRow(box)
        f.insertRow(0, "Preset", self.hud_preset)
        self.pages.addWidget(w)

    def _sync_hud_checks(self) -> None:
        h = self.settings.hud
        for key, box in self.chk.items():
            box.setChecked(bool(getattr(h, key)))

    def _build_sim(self) -> None:
        w = QWidget()
        f = QFormLayout(w)
        s = self.settings.simulation
        self.diff = _combo(["arcade", "standard", "strict"], s.difficulty)
        self.wind = _combo(["off", "low", "medium", "high"], s.wind)
        self.fail = QCheckBox("Failures")
        self.fail.setChecked(s.failures)
        self.gcol = QCheckBox("Ground Collision")
        self.gcol.setChecked(s.ground_collision)
        self.launch_assist = QCheckBox("")
        self.launch_assist.setChecked(bool(getattr(s, "launch_assist", True)))
        self.tbeh = _combo(["static", "simple", "evasive"], s.target_behaviour)
        speed_map = {0.5: "0.5×", 1.0: "1×", 2.0: "2×"}
        self.sspeed = _combo(["0.5×", "1×", "2×"], speed_map.get(s.speed, "1×"))
        f.addRow("Difficulty", self.diff)
        f.addRow("Wind", self.wind)
        f.addRow(self.fail)
        f.addRow(self.gcol)
        f.addRow(self.launch_assist)
        f.addRow("Target Behaviour", self.tbeh)
        f.addRow("Simulation Speed", self.sspeed)
        note = QLabel("Demo simulator only. Values are stored with the run when a recorder is attached.")
        note.setObjectName("Muted")
        note.setWordWrap(True)
        f.addRow(note)
        self.pages.addWidget(w)

    def _sync_lang_box(self) -> None:
        self.lang_box.blockSignals(True)
        idx = self.lang_box.findData(lang())
        if idx >= 0:
            self.lang_box.setCurrentIndex(idx)
        self.lang_box.blockSignals(False)

    def _on_lang(self) -> None:
        code = self.lang_box.currentData()
        if code:
            self.language.emit(str(code))

    def _build_system(self) -> None:
        w = QWidget()
        f = QFormLayout(w)
        self.lang_lab = QLabel("")
        self.lang_box = QComboBox()
        self.lang_box.addItem("Русский", "ru")
        self.lang_box.addItem("English", "en")
        self.lang_box.currentIndexChanged.connect(self._on_lang)
        f.addRow(self.lang_lab, self.lang_box)
        self.sys_cerber = QLabel("—")
        self.sys_ort = QLabel("—")
        self.sys_gpu = QLabel("—")
        self.sys_disp = QLabel("—")
        self.sys_fps = QLabel("—")
        self.sys_model = QLabel("—")
        self.sys_build = QLabel("—")
        for title, lab in (
            ("CERBER Backend", self.sys_cerber),
            ("ONNX Provider", self.sys_ort),
            ("GPU", self.sys_gpu),
            ("Display", self.sys_disp),
            ("Current FPS", self.sys_fps),
            ("Model", self.sys_model),
            ("Build", self.sys_build),
        ):
            lab.setObjectName("Muted")
            f.addRow(title, lab)
        logs = QPushButton("OPEN LOG DIRECTORY")
        logs.setObjectName("GhostBtn")
        logs.clicked.connect(self.open_logs.emit)
        rst = QPushButton("RESET SETTINGS")
        rst.setObjectName("GhostBtn")
        rst.clicked.connect(self.reset_settings.emit)
        rwin = QPushButton("RESET WINDOW POSITION")
        rwin.setObjectName("GhostBtn")
        rwin.clicked.connect(self.reset_window.emit)
        f.addRow(logs)
        f.addRow(rst)
        f.addRow(rwin)
        self.pages.addWidget(w)

    def set_system_info(self, info: dict[str, str]) -> None:
        self.sys_cerber.setText(info.get("cerber", "—"))
        self.sys_ort.setText(info.get("ort", "—"))
        self.sys_gpu.setText(info.get("gpu", "—"))
        self.sys_disp.setText(info.get("display", "—"))
        self.sys_fps.setText(info.get("fps", "—"))
        self.sys_model.setText(info.get("model", "—"))
        self.sys_build.setText(info.get("build", "—"))

    def collect(self) -> None:
        d = self.settings.display
        d.mode = self.mode.currentText()
        idx = self.res.currentIndex()
        if 0 <= idx < len(self._res_values):
            w, h = self._res_values[idx]
            d.resolution = [w, h]
        d.vsync = self.vsync.isChecked()
        fps_txt = self.fps.currentText()
        d.fps_limit = 0 if fps_txt == "Unlimited" else int(fps_txt)
        us = self.ui_scale.currentText().replace("%", "")
        d.ui_scale = us
        d.fov = int(self.fov.currentText())
        g = self.settings.graphics
        g.preset = self.gfx_preset.currentText()
        g.render_scale = self.render_scale.value() / 100.0
        msaa_map = {"OFF": 0, "MSAA 2×": 2, "MSAA 4×": 4, "MSAA 8×": 8}
        g.msaa = msaa_map.get(self.msaa.currentText(), 4)
        g.texture_quality = self.tex.currentText()
        g.view_distance = self.view.currentText()
        a = self.settings.audio
        a.muted = self.mute.isChecked()
        a.master = self.vol_master.value() / 100.0
        a.music = self.vol_music.value() / 100.0
        a.engine = self.vol_engine.value() / 100.0
        a.wind = self.vol_wind.value() / 100.0
        a.environment = self.vol_env.value() / 100.0
        a.ui = self.vol_ui.value() / 100.0
        a.warning = self.vol_warn.value() / 100.0
        c = self.settings.controls
        c.sensitivity = self.sens.value() / 100.0
        c.camera_sensitivity = self.cam_sens.value() / 100.0
        c.invert_y = self.invert.isChecked()
        h = self.settings.hud
        h.preset = self.hud_preset.currentText()
        for key, box in self.chk.items():
            setattr(h, key, box.isChecked())
        s = self.settings.simulation
        s.difficulty = self.diff.currentText()
        s.wind = self.wind.currentText()
        s.failures = self.fail.isChecked()
        s.ground_collision = self.gcol.isChecked()
        s.launch_assist = self.launch_assist.isChecked()
        s.target_behaviour = self.tbeh.currentText()
        s.speed = {"0.5×": 0.5, "1×": 1.0, "2×": 2.0}[self.sspeed.currentText()]
        code = self.lang_box.currentData()
        if code:
            self.settings.language = str(code)
