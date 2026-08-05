"""CERBER Studio main window — PySide6 IDE shell."""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

import cv2
import numpy as np
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QImage, QKeySequence, QPixmap, QShortcut
from PySide6.QtWidgets import (
    QDockWidget,
    QLabel,
    QMainWindow,
    QStatusBar,
    QTabWidget,
)

from .ipc import (
    DEFAULT_FRAME_ENDPOINT,
    DEFAULT_RESULT_ENDPOINT,
    FramePublisher,
    ResultSubscriber,
    VisionHealth,
)
from .overlay import draw_overlay
from .panels import (
    AircraftPanel,
    CameraPanel,
    CerberPanel,
    LogsPanel,
    TracksPanel,
    WorldPanel,
    health_line,
)
from .viewport import ViewportWidget

STUDIO_ROOT = Path(__file__).resolve().parents[1]
WORKER_SCRIPT = STUDIO_ROOT / "worker" / "cerber_worker.py"


class StudioWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("NULLXES CERBER Studio v1")
        self.resize(1400, 860)

        self.viewport = ViewportWidget(self)
        self.setCentralWidget(self.viewport)

        self.world = WorldPanel()
        self.camera = CameraPanel()
        self.aircraft = AircraftPanel()
        self.cerber = CerberPanel()
        self.tracks = TracksPanel()
        self.logs = LogsPanel()

        self._add_dock("WORLD", self.world, Qt.LeftDockWidgetArea)
        self._add_dock("CAMERA", self.camera, Qt.LeftDockWidgetArea)
        self._add_dock("AIRCRAFT", self.aircraft, Qt.LeftDockWidgetArea)
        tabs = QTabWidget()
        tabs.addTab(self.cerber, "CERBER")
        tabs.addTab(self.tracks, "TRACKS")
        tabs.addTab(self.logs, "LOGS")
        dock_r = QDockWidget("CERBER / TRACKS / LOGS", self)
        dock_r.setWidget(tabs)
        self.addDockWidget(Qt.RightDockWidgetArea, dock_r)

        self.status = QStatusBar()
        self.setStatusBar(self.status)
        self.status.showMessage("STUDIO V1 · VIRTUAL WORLD · NOT TWIN")

        self._worker: subprocess.Popen | None = None
        self._frame_pub: FramePublisher | None = None
        self._result_sub: ResultSubscriber | None = None
        self._config = "detector_alpha_v2.yaml"
        self._last_health = VisionHealth(detail="worker not started")
        self._pip = QLabel()
        self._pip.setFixedHeight(200)
        self._pip.setStyleSheet("background:#000;")
        dock_pip = QDockWidget("CERBER EYE", self)
        dock_pip.setWidget(self._pip)
        self.addDockWidget(Qt.BottomDockWidgetArea, dock_pip)

        self.world.reset_target.connect(self._on_reset_target)
        self.world.reset_ego.connect(self._on_reset_ego)
        self.camera.mode_changed.connect(self._on_camera_mode)
        self.aircraft.preset_changed.connect(self._on_preset)
        self.aircraft.mode_changed.connect(self._on_flight_mode)
        self.cerber.start_worker.connect(self.start_worker)
        self.cerber.stop_worker.connect(self.stop_worker)
        self.cerber.config_changed.connect(self._on_config)

        QShortcut(QKeySequence("F1"), self, activated=self._on_reset_target)
        QShortcut(QKeySequence("R"), self, activated=self._on_reset_ego)
        QShortcut(QKeySequence("1"), self, activated=lambda: self._set_mode("MANUAL"))
        QShortcut(QKeySequence("2"), self, activated=lambda: self._set_mode("ASSIST"))
        QShortcut(QKeySequence("3"), self, activated=lambda: self._set_mode("PURSUIT"))

        self.viewport.set_frame_callback(self._on_frame, every=3)
        self.viewport.setFocus()

        self._ui_timer = QTimer(self)
        self._ui_timer.timeout.connect(self._poll)
        self._ui_timer.start(50)

        self.logs.append("NULLXES CERBER Studio v1 ready")
        self.logs.append("Start CERBER worker from CERBER panel when ready")

    def _add_dock(self, title: str, widget, area) -> None:
        dock = QDockWidget(title, self)
        dock.setWidget(widget)
        self.addDockWidget(area, dock)

    def _on_reset_target(self) -> None:
        self.viewport.engine.reset_target()
        self.logs.append("WORLD: target reset")

    def _on_reset_ego(self) -> None:
        self.viewport.engine.reset_ego()
        self.logs.append("WORLD: ego reset")

    def _on_camera_mode(self, mode: str) -> None:
        self.viewport.engine.camera_mode = mode
        self.logs.append(f"CAMERA: {mode}")

    def _on_preset(self, key: str) -> None:
        self.viewport.engine.set_aircraft(key)
        self.logs.append(f"AIRCRAFT: {key}")

    def _on_flight_mode(self, mode: str) -> None:
        self.viewport.engine.flight_mode = mode
        self.logs.append(f"MODE: {mode}")

    def _set_mode(self, mode: str) -> None:
        idx = self.aircraft.flight.findText(mode)
        if idx >= 0:
            self.aircraft.flight.setCurrentIndex(idx)

    def _on_config(self, name: str) -> None:
        self._config = name
        self.logs.append(f"CERBER config → {name} (restart worker to apply)")

    def start_worker(self) -> None:
        self.stop_worker()
        if self._frame_pub is None:
            self._frame_pub = FramePublisher(DEFAULT_FRAME_ENDPOINT)
            time.sleep(0.15)
        if self._result_sub is None:
            self._result_sub = ResultSubscriber(DEFAULT_RESULT_ENDPOINT)
        cmd = [
            sys.executable,
            str(WORKER_SCRIPT),
            "--config",
            self._config,
            "--frames",
            DEFAULT_FRAME_ENDPOINT,
            "--results",
            DEFAULT_RESULT_ENDPOINT,
        ]
        self._worker = subprocess.Popen(
            cmd,
            cwd=str(STUDIO_ROOT),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )
        self.cerber.set_status(f"Worker: running pid={self._worker.pid} cfg={self._config}")
        self.logs.append(f"CERBER worker started pid={self._worker.pid}")
        # ZMQ PUB slow-joiner
        time.sleep(0.3)

    def stop_worker(self) -> None:
        if self._worker is not None:
            self._worker.terminate()
            try:
                self._worker.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self._worker.kill()
            self.logs.append("CERBER worker stopped")
            self._worker = None
        self.cerber.set_status("Worker: stopped")

    def _on_frame(self, bgr: np.ndarray) -> None:
        if self._frame_pub is None or self._worker is None:
            return
        try:
            self._frame_pub.send(bgr, {"source": "nose"})
        except Exception as exc:  # noqa: BLE001
            self.logs.append(f"frame pub error: {exc}")

    def _poll(self) -> None:
        eng = self.viewport.engine
        st = eng.dynamics.state
        self.aircraft.set_telem(st.speed, st.z, st.throttle)
        self.world.set_distance(eng.target_distance())

        if self._result_sub is not None:
            res = self._result_sub.recv()
            while True:
                nxt = self._result_sub.recv()
                if nxt is None:
                    break
                res = nxt
            if res is not None:
                self._last_health = res.health
                self.tracks.set_tracks(res.tracks)
                self.cerber.set_status(health_line(res.health))
                if res.jpeg:
                    arr = np.frombuffer(res.jpeg, dtype=np.uint8)
                    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
                    if img is not None:
                        rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                        h, w, _ = rgb.shape
                        qimg = QImage(rgb.data, w, h, 3 * w, QImage.Format_RGB888).copy()
                        self._pip.setPixmap(
                            QPixmap.fromImage(qimg).scaled(
                                self._pip.size(),
                                Qt.KeepAspectRatio,
                                Qt.SmoothTransformation,
                            )
                        )
                elif self.viewport.last_rgb is not None:
                    bgr = self.viewport.last_rgb[:, :, ::-1].copy()
                    drawn = draw_overlay(
                        bgr,
                        res.detections,
                        res.tracks,
                        res.health,
                        eng.flight_mode,
                    )
                    rgb = cv2.cvtColor(drawn, cv2.COLOR_BGR2RGB)
                    h, w, _ = rgb.shape
                    qimg = QImage(rgb.data, w, h, 3 * w, QImage.Format_RGB888).copy()
                    self._pip.setPixmap(
                        QPixmap.fromImage(qimg).scaled(
                            self._pip.size(),
                            Qt.KeepAspectRatio,
                            Qt.SmoothTransformation,
                        )
                    )

        alive = self._worker is not None and self._worker.poll() is None
        if self._worker is not None and not alive:
            err = ""
            if self._worker.stderr is not None:
                err = self._worker.stderr.read().decode("utf-8", errors="replace")[-300:]
            self.cerber.set_status(f"Worker: exited {self._worker.returncode} {err}")
            self._worker = None

        self.status.showMessage(
            f"STUDIO V1 · VIRTUAL WORLD · NOT TWIN · "
            f"render {eng.render_fps:.0f} FPS · "
            f"worker {'UP' if alive else 'DOWN'} · "
            f"CERBER {'OK' if self._last_health.vision_ok else 'BLOCKED'}"
        )

    def closeEvent(self, event) -> None:
        self.stop_worker()
        if self._frame_pub is not None:
            self._frame_pub.close()
        if self._result_sub is not None:
            self._result_sub.close()
        try:
            self.viewport.engine.close_engine()
        except Exception:  # noqa: BLE001
            pass
        super().closeEvent(event)
