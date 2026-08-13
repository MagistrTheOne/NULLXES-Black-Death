"""Simulation session: aircraft/mission apply + CERBER worker lifecycle."""

from __future__ import annotations

import logging
import subprocess
import sys
import time

from .aircraft.definition import AircraftDefinition
from .aircraft.registry import AircraftRegistry
from .config.paths import STUDIO_ROOT
from .ipc import (
    DEFAULT_FRAME_ENDPOINT,
    DEFAULT_RESULT_ENDPOINT,
    FramePublisher,
    ResultSubscriber,
    VisionHealth,
)
from .missions.registry import MissionDefinition
from .viewport import ViewportWidget

log = logging.getLogger("cerber_studio.session")
WORKER_SCRIPT = STUDIO_ROOT / "worker" / "cerber_worker.py"


class SimulationSession:
    def __init__(self, viewport: ViewportWidget, registry: AircraftRegistry) -> None:
        self.viewport = viewport
        self.registry = registry
        self.worker: subprocess.Popen | None = None
        self.frame_pub: FramePublisher | None = None
        self.result_sub: ResultSubscriber | None = None
        self.health = VisionHealth(detail="worker not started")
        self.config_name = "detector_alpha_v2.yaml"
        self.aircraft: AircraftDefinition | None = None
        self.target: AircraftDefinition | None = None
        self.mission: MissionDefinition | None = None
        self.last_track_id: int | None = None
        self.last_detections: list = []
        self.last_tracks: list = []
        self.engine = viewport.engine
        self.engine._registry = registry

    @property
    def worker_alive(self) -> bool:
        return self.worker is not None and self.worker.poll() is None

    @property
    def vision_ready(self) -> bool:
        return self.worker_alive and bool(self.health.vision_ok)

    def apply_aircraft(self, defn: AircraftDefinition) -> str:
        self.aircraft = defn
        return self.engine.apply_definition(defn)

    def apply_target(self, defn: AircraftDefinition | None) -> str:
        self.target = defn
        return self.engine.apply_target_definition(defn)

    def apply_mission(self, mission: MissionDefinition) -> None:
        self.mission = mission
        self.engine.target_visible = bool(mission.target)
        self.engine.mission_waypoints = [(w.x, w.y, w.z, w.radius_m) for w in mission.waypoints]
        self.engine.mission_i = 0
        if mission.type == "target_follow":
            self.engine.flight_mode = "PURSUIT"
            self.engine.camera_mode = "chase"
        else:
            self.engine.flight_mode = "MANUAL"
            self.engine.camera_mode = "chase"

    def start_world(self) -> None:
        self.engine.set_scene_mode("flight")
        self.engine.paused = False
        self.engine.input_enabled = True
        self.engine.reset_ego()
        self.engine.launch()
        self.engine.reset_target()

    def restart(self) -> None:
        self.engine.reset_ego()
        self.engine.launch()
        self.engine.reset_target()
        self.engine.paused = False
        self.engine.input_enabled = True

    def start_worker(self) -> str:
        self.stop_worker()
        try:
            if self.frame_pub is None:
                self.frame_pub = FramePublisher(DEFAULT_FRAME_ENDPOINT)
                time.sleep(0.15)
            if self.result_sub is None:
                self.result_sub = ResultSubscriber(DEFAULT_RESULT_ENDPOINT)
            cmd = [
                sys.executable,
                str(WORKER_SCRIPT),
                "--config",
                self.config_name,
                "--frames",
                DEFAULT_FRAME_ENDPOINT,
                "--results",
                DEFAULT_RESULT_ENDPOINT,
            ]
            self.worker = subprocess.Popen(
                cmd,
                cwd=str(STUDIO_ROOT),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
            )
            time.sleep(0.3)
            return f"worker pid={self.worker.pid}"
        except Exception as exc:  # noqa: BLE001
            log.exception("CERBER worker failed: %s", exc)
            self.health = VisionHealth(detail=f"unavailable: {exc}")
            return str(exc)

    def stop_worker(self) -> None:
        if self.worker is not None:
            self.worker.terminate()
            try:
                self.worker.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.worker.kill()
            self.worker = None
        self.health = VisionHealth(detail="worker not started")

    def on_frame(self, bgr) -> None:
        if self.frame_pub is None or self.worker is None:
            return
        try:
            self.frame_pub.send(bgr, {"source": "nose"})
        except Exception as exc:  # noqa: BLE001
            log.warning("frame pub: %s", exc)

    def poll_results(self) -> None:
        if self.result_sub is None:
            return
        res = self.result_sub.recv()
        while True:
            nxt = self.result_sub.recv()
            if nxt is None:
                break
            res = nxt
        if res is not None:
            self.health = res.health
            self.last_detections = res.detections
            self.last_tracks = res.tracks
            if res.tracks:
                self.last_track_id = int(res.tracks[0].track_id)
            else:
                self.last_track_id = None
        if self.worker is not None and self.worker.poll() is not None:
            err = ""
            if self.worker.stderr is not None:
                err = self.worker.stderr.read().decode("utf-8", errors="replace")[-300:]
            log.warning("CERBER worker exited %s %s", self.worker.returncode, err)
            self.health = VisionHealth(detail=f"exited {self.worker.returncode}")
            self.worker = None

    def teardown(self) -> None:
        self.stop_worker()
        if self.frame_pub is not None:
            self.frame_pub.close()
            self.frame_pub = None
        if self.result_sub is not None:
            self.result_sub.close()
            self.result_sub = None
        self.engine.input_enabled = False
        self.engine.paused = False
        self.engine.set_scene_mode("hangar")
        self.engine.keys.clear()
