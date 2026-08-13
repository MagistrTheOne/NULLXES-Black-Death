"""Panda3D offscreen engine + multi-rate S1 loop."""

from __future__ import annotations

import time
from pathlib import Path

import numpy as np
import yaml
from panda3d.core import (
    AmbientLight,
    DirectionalLight,
    GraphicsOutput,
    PerspectiveLens,
    Texture,
    Vec3,
    loadPrcFileData,
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QImage, QKeyEvent, QPixmap
from PySide6.QtWidgets import QLabel, QSizePolicy, QVBoxLayout, QWidget

loadPrcFileData("", "window-type offscreen")
loadPrcFileData("", "audio-library-name null")
loadPrcFileData("", "framebuffer-hardware true")
loadPrcFileData("", "sync-video false")
loadPrcFileData("", "show-frame-rate-meter 0")
loadPrcFileData("", "notify-level-util error")
loadPrcFileData("", "notify-level-glgsg error")

from direct.showbase.ShowBase import ShowBase  # noqa: E402

from .camera import LatencyCam
from .cerber_bridge import CerberBridge
from .clocks import Accumulator, RateBudget
from .entities import BackgroundFlock, TargetScript, los_to_target
from .events import EventKind, SimEvent
from .hud import format_hud, make_hud
from .pilot import DemoPilot, Stick
from .recorder import JsonlRecorder
from .sensors import derived
from .vehicle import Vehicle
from .world import ASSETS, attach_ego, attach_extra, attach_ground, attach_target

ROOT = Path(__file__).resolve().parents[1]


class SimEngine(ShowBase):
    def __init__(self, width: int = 1280, height: int = 720) -> None:
        loadPrcFileData("", f"win-size {int(width)} {int(height)}")
        ShowBase.__init__(self, windowType="offscreen")
        self.disableMouse()
        self.win_w = width
        self.win_h = height
        self.setBackgroundColor(0.42, 0.52, 0.68, 1.0)
        self.color_tex = Texture()
        self.win.addRenderTexture(
            self.color_tex,
            GraphicsOutput.RTMCopyRam,
            GraphicsOutput.RTPColor,
        )
        alight = AmbientLight("alight")
        alight.setColor((0.55, 0.55, 0.6, 1))
        self.render.setLight(self.render.attachNewNode(alight))
        dlight = DirectionalLight("dlight")
        dlight.setDirection(Vec3(-0.6, -0.8, -1))
        dlight.setColor((0.9, 0.9, 0.85, 1))
        self.render.setLight(self.render.attachNewNode(dlight))

        man = yaml.safe_load((ASSETS / "manifest.yaml").read_text(encoding="utf-8")) or {}
        scale = float(man.get("scale", 1.0))
        attach_ground(self.render)
        self.ego_np = attach_ego(self.render, self.loader, glb_name=str(man.get("ego", "x8.glb")), scale=scale)
        self.target_np = attach_target(
            self.render, self.loader, glb_name=str(man.get("target", "target.glb")), scale=scale
        )
        self.bg_nps = [attach_extra(self.render, i) for i in range(8)]
        self.nose_np = self.ego_np.attachNewNode("nose")
        self.nose_np.setPos(0, 0.4, 0.12)
        self.camLens = PerspectiveLens()
        self.camLens.setFov(70)
        self.camLens.setNearFar(0.2, 4000)
        self.cam.node().setLens(self.camLens)

        self.vehicle = Vehicle()
        self.target = TargetScript()
        self.flock = BackgroundFlock(8)
        self.pilot = DemoPilot()
        self.cam_lat = LatencyCam(2)
        self.cerber = CerberBridge()
        self.keys: set[str] = set()
        self.launch_edge = False
        self.last_event = ""
        self.last_rgb = np.zeros((height, width, 3), dtype=np.uint8)
        self._last_wall = time.perf_counter()
        self.rates = RateBudget()
        self.acc_phys = Accumulator(self.rates.physics_hz)
        self.acc_pilot = Accumulator(self.rates.pilot_hz)
        self.acc_cam = Accumulator(self.rates.camera_hz)
        self.acc_cer = Accumulator(self.rates.cerber_hz)
        self.acc_log = Accumulator(self.rates.log_hz)
        self.acc_hud = Accumulator(self.rates.hud_hz)
        log_dir = ROOT / "runs"
        stamp = time.strftime("%Y%m%d_%H%M%S")
        self.recorder = JsonlRecorder(log_dir / f"bd_sim_{stamp}.jsonl")
        self.hud_text = ""
        self.stick = Stick()
        self.mission_path = ROOT / "missions" / "demo_patrol.yaml"
        self._latched: set[str] = set()

        self.camera.reparentTo(self.nose_np)
        self.camera.setPos(0, 0, 0)
        self.camera.setHpr(0, 0, 0)

    def reset(self) -> None:
        self.vehicle.reset()
        self.target.reset()
        self.pilot.set_mode("MANUAL")
        self.last_event = ""

    def step(self) -> np.ndarray:
        now = time.perf_counter()
        wall = now - self._last_wall
        self._last_wall = now
        events: list[SimEvent] = []

        n_phys = self.acc_phys.add(wall)
        n_pilot = self.acc_pilot.add(wall)
        n_cam = self.acc_cam.add(wall)
        n_cer = self.acc_cer.add(wall)
        n_log = self.acc_log.add(wall)
        n_hud = self.acc_hud.add(wall)

        launch = self.launch_edge
        self.launch_edge = False
        self.stick = Stick(
            pitch=float(("s" in self.keys) - ("w" in self.keys)),
            roll=float(("d" in self.keys) - ("a" in self.keys)),
            yaw=float(-1.0 if "q" in self.keys else 0.0),
            throttle=float(
                (("shift" in self.keys) - ("control" in self.keys))
            ),
            launch=launch,
        )

        cmd = self.stick
        for _ in range(n_pilot):
            dist, bearing, _dz = los_to_target(self.vehicle.state, self.target)
            in_fov = abs(((bearing - self.vehicle.state.yaw_deg + 180) % 360) - 180) < 35.0
            has_track = self.cerber.has_track or (in_fov and dist < 220.0)
            cmd, ev = self.pilot.step(
                self.acc_pilot.dt,
                cmd,
                self.vehicle.state,
                self.target,
                self.vehicle.state.t,
                has_track,
            )
            events.extend(ev)

        for _ in range(n_phys):
            flags = self.vehicle.step(
                self.acc_phys.dt,
                pitch_cmd=cmd.pitch,
                roll_cmd=cmd.roll,
                yaw_cmd=cmd.yaw,
                throttle_cmd=cmd.throttle,
                launch=cmd.launch,
            )
            cmd.launch = False
            self.target.step(self.acc_phys.dt)
            t = self.vehicle.state.t
            for kind in flags:
                if kind in self._latched and kind in {"STALL", "LOW_ALTITUDE", "EXCESSIVE_BANK", "OVERSPEED"}:
                    continue
                self._latched.add(kind)
                events.append(SimEvent(EventKind(kind), t, kind))
            for kind in ("STALL", "LOW_ALTITUDE", "EXCESSIVE_BANK", "OVERSPEED"):
                if kind not in flags:
                    self._latched.discard(kind)

        s = self.vehicle.state
        self.ego_np.setPos(s.x, s.y, s.z)
        self.ego_np.setHpr(s.yaw_deg, s.pitch_deg, s.roll_deg)
        tx, ty, tz = self.target.position()
        self.target_np.setPos(tx, ty, tz)
        self.target_np.setH(self.target.yaw_deg)
        for np_, pose in zip(self.bg_nps, self.flock.poses(s.t), strict=False):
            np_.setPos(pose[0], pose[1], pose[2])
            np_.setH(pose[3])

        self.taskMgr.step()
        rgb = self._grab_rgb()
        delayed = rgb
        if n_cam:
            delayed = self.cam_lat.push(rgb)
        self.last_rgb = delayed

        if n_cer and self.cerber.enabled:
            self.cerber.send_frame(delayed[:, :, ::-1].copy())
            self.cerber.poll()

        dist, _b, _ = los_to_target(s, self.target)
        if n_hud:
            self.hud_text = format_hud(
                mode=self.pilot.mode,
                tas=s.airspeed,
                alt=s.z,
                thr=s.throttle,
                alpha=s.alpha_deg,
                launched=s.launched,
                crashed=s.crashed,
                stalled=s.stalled,
                event=self.last_event,
                cerber=self.cerber.detail,
                mission=f"{self.pilot.mission.name} {self.pilot.mission.idx}/{len(self.pilot.mission.waypoints)}",
                dist=dist,
            )
        if events:
            self.last_event = events[-1].kind.value
        if n_log:
            row = {
                "t": s.t,
                "vehicle_state": {
                    "x": s.x,
                    "y": s.y,
                    "z": s.z,
                    "yaw": s.yaw_deg,
                    "pitch": s.pitch_deg,
                    "roll": s.roll_deg,
                    "tas": s.airspeed,
                    "thr": s.throttle,
                    "launched": s.launched,
                    "crashed": s.crashed,
                },
                "control_input": {
                    "pitch": cmd.pitch,
                    "roll": cmd.roll,
                    "yaw": cmd.yaw,
                    "thr": cmd.throttle,
                },
                "mode": self.pilot.mode,
                "sensor_metadata": derived(s),
                "tracks": self.cerber.tracks,
                "mission_state": {
                    "name": self.pilot.mission.name,
                    "idx": self.pilot.mission.idx,
                    "done": self.pilot.mission.done,
                },
                "events": [e.as_dict() for e in events],
            }
            self.recorder.write(row)
        elif events:
            self.recorder.write(
                {"t": s.t, "events": [e.as_dict() for e in events], "mode": self.pilot.mode}
            )
        return delayed

    def _grab_rgb(self) -> np.ndarray:
        if not self.color_tex.hasRamImage():
            return np.zeros((self.win_h, self.win_w, 3), dtype=np.uint8)
        data = self.color_tex.getRamImageAs("RGB")
        arr = np.frombuffer(data, dtype=np.uint8)
        w = self.color_tex.getXSize()
        h = self.color_tex.getYSize()
        if arr.size < w * h * 3:
            return np.zeros((self.win_h, self.win_w, 3), dtype=np.uint8)
        return np.flipud(arr.reshape((h, w, 3))).copy()

    def close_engine(self) -> None:
        self.recorder.close()
        self.cerber.close()
        ShowBase.destroy(self)


class SimViewport(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.view = QLabel(self)
        self.view.setAlignment(Qt.AlignCenter)
        self.view.setStyleSheet("background:#050505;")
        self.hud = make_hud(self)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self.view)
        self.engine = SimEngine()
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(16)

    def _tick(self) -> None:
        rgb = self.engine.step()
        h, w, _ = rgb.shape
        qimg = QImage(rgb.data, w, h, 3 * w, QImage.Format_RGB888).copy()
        self.view.setPixmap(
            QPixmap.fromImage(qimg).scaled(self.view.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        )
        self.hud.setText(self.engine.hud_text)
        self.hud.adjustSize()
        self.hud.move(12, 12)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        key = event.key()
        if key == Qt.Key_E and not event.isAutoRepeat():
            self.engine.launch_edge = True
        mapping = {
            Qt.Key_W: "w",
            Qt.Key_S: "s",
            Qt.Key_A: "a",
            Qt.Key_D: "d",
            Qt.Key_Q: "q",
            Qt.Key_Shift: "shift",
            Qt.Key_Control: "control",
        }
        name = mapping.get(key)
        if name:
            self.engine.keys.add(name)
        if key == Qt.Key_1:
            self.engine.pilot.set_mode("MANUAL")
        elif key == Qt.Key_2:
            self.engine.pilot.set_mode("ASSIST")
        elif key == Qt.Key_3:
            self.engine.pilot.set_mode("FOLLOW")
        elif key == Qt.Key_4:
            self.engine.pilot.load_mission(self.engine.mission_path, self.engine.vehicle.state.t)
        elif key == Qt.Key_R:
            self.engine.reset()
        elif key == Qt.Key_F1:
            self.engine.target.reset()
        super().keyPressEvent(event)

    def keyReleaseEvent(self, event: QKeyEvent) -> None:
        mapping = {
            Qt.Key_W: "w",
            Qt.Key_S: "s",
            Qt.Key_A: "a",
            Qt.Key_D: "d",
            Qt.Key_Q: "q",
            Qt.Key_Shift: "shift",
            Qt.Key_Control: "control",
        }
        name = mapping.get(event.key())
        if name:
            self.engine.keys.discard(name)
        super().keyReleaseEvent(event)
