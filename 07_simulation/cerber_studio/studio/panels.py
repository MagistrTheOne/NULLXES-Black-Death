"""Working dock panels for CERBER Studio."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QPlainTextEdit,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from .dynamics import PRESETS
from .ipc import TrackRow, VisionHealth


class WorldPanel(QWidget):
    reset_target = Signal()
    reset_ego = Signal()

    def __init__(self) -> None:
        super().__init__()
        lay = QVBoxLayout(self)
        box = QGroupBox("WORLD")
        fl = QVBoxLayout(box)
        b1 = QPushButton("Reset target orbit (F1)")
        b2 = QPushButton("Reset ego (R)")
        b1.clicked.connect(self.reset_target.emit)
        b2.clicked.connect(self.reset_ego.emit)
        fl.addWidget(b1)
        fl.addWidget(b2)
        self.dist_label = QLabel("Target dist: —")
        fl.addWidget(self.dist_label)
        lay.addWidget(box)
        lay.addStretch(1)

    def set_distance(self, d: float) -> None:
        self.dist_label.setText(f"Target dist: {d:.1f} m")


class CameraPanel(QWidget):
    mode_changed = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        lay = QVBoxLayout(self)
        box = QGroupBox("CAMERA")
        fl = QFormLayout(box)
        self.combo = QComboBox()
        self.combo.addItems(["nose", "chase"])
        self.combo.currentTextChanged.connect(self.mode_changed.emit)
        fl.addRow("View", self.combo)
        lay.addWidget(box)
        lay.addStretch(1)


class AircraftPanel(QWidget):
    preset_changed = Signal(str)
    mode_changed = Signal(str)

    def __init__(self, registry=None) -> None:
        super().__init__()
        lay = QVBoxLayout(self)
        box = QGroupBox("AIRCRAFT")
        fl = QFormLayout(box)
        self.preset = QComboBox()
        if registry is not None:
            for defn in registry.items:
                mark = "  [UNCONFIGURED]" if defn.unconfigured else ""
                self.preset.addItem(defn.name + mark, defn.id)
        else:
            for key, p in PRESETS.items():
                self.preset.addItem(p.title, key)
            if self.preset.count() > 1:
                self.preset.setCurrentIndex(1)
        self.preset.currentIndexChanged.connect(self._emit_preset)
        self.flight = QComboBox()
        self.flight.addItems(["MANUAL", "ASSIST", "PURSUIT", "MISSION"])
        self.flight.currentTextChanged.connect(self.mode_changed.emit)
        fl.addRow("Aircraft", self.preset)
        fl.addRow("Mode", self.flight)
        self.telem = QLabel("SPD —  ALT —  THR —")
        fl.addRow(self.telem)
        lay.addWidget(box)
        tip = QLabel("WASD pitch/roll · QE yaw · Shift/Ctrl throttle")
        tip.setWordWrap(True)
        lay.addWidget(tip)
        lay.addStretch(1)

    def _emit_preset(self) -> None:
        self.preset_changed.emit(self.preset.currentData())

    def set_telem(self, spd: float, alt: float, thr: float) -> None:
        self.telem.setText(f"SPD {spd:.1f}  ALT {alt:.1f}  THR {thr:.2f}")


class CerberPanel(QWidget):
    start_worker = Signal()
    stop_worker = Signal()
    config_changed = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        lay = QVBoxLayout(self)
        box = QGroupBox("CERBER")
        fl = QFormLayout(box)
        self.cfg = QComboBox()
        self.cfg.addItems(
            [
                "detector_alpha_v2.yaml",
                "detector_alpha_v2b.yaml",
                "detector_alpha.yaml",
            ]
        )
        self.cfg.currentTextChanged.connect(self.config_changed.emit)
        fl.addRow("Config", self.cfg)
        row = QHBoxLayout()
        self.btn_start = QPushButton("Start worker")
        self.btn_stop = QPushButton("Stop worker")
        self.btn_start.clicked.connect(self.start_worker.emit)
        self.btn_stop.clicked.connect(self.stop_worker.emit)
        row.addWidget(self.btn_start)
        row.addWidget(self.btn_stop)
        fl.addRow(row)
        self.status = QLabel("Worker: stopped")
        self.status.setWordWrap(True)
        fl.addRow(self.status)
        lay.addWidget(box)
        lay.addStretch(1)

    def set_status(self, text: str) -> None:
        self.status.setText(text)


class TracksPanel(QWidget):
    def __init__(self) -> None:
        super().__init__()
        lay = QVBoxLayout(self)
        box = QGroupBox("TRACKS")
        vl = QVBoxLayout(box)
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["ID", "class", "conf", "x1", "y1"])
        vl.addWidget(self.table)
        lay.addWidget(box)

    def set_tracks(self, tracks: list[TrackRow]) -> None:
        self.table.setRowCount(len(tracks))
        for i, t in enumerate(tracks):
            vals = [str(t.track_id), t.name, f"{t.conf:.2f}", f"{t.x1:.0f}", f"{t.y1:.0f}"]
            for j, v in enumerate(vals):
                self.table.setItem(i, j, QTableWidgetItem(v))


class LogsPanel(QWidget):
    def __init__(self) -> None:
        super().__init__()
        lay = QVBoxLayout(self)
        box = QGroupBox("LOGS")
        vl = QVBoxLayout(box)
        self.text = QPlainTextEdit()
        self.text.setReadOnly(True)
        self.text.setMaximumBlockCount(500)
        vl.addWidget(self.text)
        lay.addWidget(box)

    def append(self, line: str) -> None:
        self.text.appendPlainText(line)


def health_line(h: VisionHealth) -> str:
    state = "OK" if h.vision_ok else "BLOCKED"
    return f"CERBER {state}: {h.detail} · infer {h.infer_fps:.1f} FPS"
