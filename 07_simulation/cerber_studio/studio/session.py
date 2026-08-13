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
from .missions.director import OperationDirector
from .missions.registry import MissionDefinition
from .pilot import PilotRecord
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
        self.pilot = PilotRecord.load()
        self.flight_dir = None
        self._end_logged = False
        self.director = OperationDirector()
        self._prev_track: int | None = None

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
        if mission.region:
            self.engine.settings.session.region_id = mission.region
        if mission.time in ("clear", "sunset", "overcast", "night", "rain", "fog", "storm"):
            self.engine.settings.session.weather = mission.time
        elif mission.weather:
            self.engine.settings.session.weather = mission.weather
        if mission.type == "target_follow":
            self.engine.flight_mode = "PURSUIT"
            self.engine.camera_mode = "chase"
        else:
            self.engine.flight_mode = "MANUAL"
            self.engine.camera_mode = "chase"
        if mission.assist is False:
            self.engine._mission_assist = False
        elif mission.assist is True:
            self.engine._mission_assist = True
        else:
            self.engine._mission_assist = None
        self.engine.dynamics.set_launch_assist(
            bool(self.engine.settings.simulation.launch_assist if self.engine._mission_assist is None else self.engine._mission_assist)
        )
        self.engine._mission_wind = mission.wind or None
        self.director.load(mission)

    def start_world(self) -> None:
        self.engine.set_scene_mode("flight")
        self.engine.prepare_world()
        self.engine.paused = False
        self.engine.input_enabled = True
        self.engine.spawn_ready()
        self.engine.reset_target()
        self._end_logged = False
        self.director.success = False
        self.director.failed = False
        if self.mission is not None:
            self.director.load(self.mission)
        from .sim.world_contract import aircraft_profile_hash, build_contract

        clock = self.engine.world.atmosphere.time_of_day_h
        hh = int(clock) % 24
        mm = int((clock % 1.0) * 60)
        contract = build_contract(
            seed=int(self.engine.settings.session.world_seed),
            region=str(self.engine.settings.session.region_id or ""),
            aircraft_id=self.aircraft.id if self.aircraft else "",
            profile_hash=aircraft_profile_hash(self.aircraft) if self.aircraft else "",
            dynamics_backend=getattr(self.engine.dynamics, "name", "arcade"),
            initial_time=f"{hh:02d}:{mm:02d}",
            time_flow=str(self.engine.world.atmosphere.time_flow),
        )
        self.engine.blackbox_contract = contract
        meta = {
            "aircraft": self.aircraft.id if self.aircraft else "",
            "mission": self.mission.id if self.mission else "",
            "region": self.engine.settings.session.region_id,
            "seed": self.engine.settings.session.world_seed,
            "weather": self.engine.settings.session.weather,
            **contract,
        }
        self.flight_dir = self.engine.blackbox.start(meta)
        if self.mission is not None and self.mission.id == "flight_training":
            self.engine.training.start(self.engine.dynamics.state.yaw_deg)
        else:
            self.engine.training.stop()

    def restart(self) -> None:
        self.start_world()

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
                tid = int(res.tracks[0].track_id)
                if self.last_track_id is None:
                    st = self.engine.dynamics.state
                    self.engine.blackbox.event("CERBER_ACQUIRE", {"id": tid}, t=float(st.flight_time))
                self.last_track_id = tid
            else:
                if self.last_track_id is not None:
                    st = self.engine.dynamics.state
                    self.engine.blackbox.event("CERBER_LOST", {"id": self.last_track_id}, t=float(st.flight_time))
                self.last_track_id = None
        if self.worker is not None and self.worker.poll() is not None:
            err = ""
            if self.worker.stderr is not None:
                err = self.worker.stderr.read().decode("utf-8", errors="replace")[-300:]
            log.warning("CERBER worker exited %s %s", self.worker.returncode, err)
            self.health = VisionHealth(detail=f"exited {self.worker.returncode}")
            self.worker = None

    def tick_ops(self, dt: float) -> None:
        if self.mission is None:
            return
        if self.mission.type == "free_flight" and not self.mission.challenge:
            return
        eng = self.engine
        st = eng.dynamics.state
        on_rw = eng.world.graph.airfield_mask(st.x, st.y)
        dist = eng.target_distance() if eng.target_visible else None
        assist = bool(eng.settings.simulation.launch_assist)
        if self.mission.assist is False:
            assist = False
        phase = st.phase.value if hasattr(st.phase, "value") else str(st.phase)
        self.director.update(
            dt,
            phase=phase,
            agl=st.agl,
            speed=st.speed,
            dist_target=dist,
            track_id=self.last_track_id,
            landing_grade=st.landing_grade,
            assist=assist,
            vz=float(st.vz),
            on_runway=on_rw,
        )

    def tick_discovery(self) -> None:
        t = float(self.engine.dynamics.state.flight_time)
        for title in self.engine.discovered_now:
            if self.pilot.discover(title):
                self.engine.blackbox.event("DISCOVER", {"title": title}, t=t)

    def finish_flight(self) -> None:
        if self._end_logged:
            return
        self._end_logged = True
        st = self.engine.dynamics.state
        self.engine.blackbox.event("COMPLETE", {"grade": st.landing_grade, "km": st.distance_m / 1000.0}, t=float(st.flight_time))
        self.engine.blackbox.close()
        self.pilot.apply_flight(
            time_s=st.flight_time,
            distance_m=st.distance_m,
            grade=st.landing_grade,
            mission_id=self.mission.id if self.mission else "",
        )
        if self.director.success and self.mission is not None and self.mission.challenge:
            self.pilot.certify(self.mission.name, dict(self.director.grade))
        if self.director.unlock in ("night_watch", "FOLLOW", "follow"):
            self.pilot.night_unlocked = True
            self.pilot.follow_cleared = True
            self.pilot.save()

    def teardown(self) -> None:
        self.engine.blackbox.close()
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
        self.engine._mission_wind = None
        self.engine._mission_assist = None
        self.engine.world.atmosphere.set_visual_clock(None)
