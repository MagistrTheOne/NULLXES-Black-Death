"""Panda3D offscreen engine painted into a Qt widget."""

from __future__ import annotations

import math
import time
from typing import Callable

import numpy as np
from panda3d.core import (
    AmbientLight,
    DirectionalLight,
    GraphicsOutput,
    PerspectiveLens,
    Texture,
    Vec3,
)
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QImage, QKeyEvent, QMouseEvent, QPixmap, QWheelEvent
from PySide6.QtWidgets import QLabel, QSizePolicy, QVBoxLayout, QWidget

from direct.showbase.ShowBase import ShowBase

from .aircraft.definition import AircraftDefinition
from .aircraft.loader import load_visual, to_wing_params
from .config.settings import DEFAULT_BINDINGS, UserSettings
from .display import apply_panda_prc, apply_texture_quality, view_distance_far
from .dynamics import ArcadeDynamics, preset
from .world import attach_ground, attach_hangar, attach_target, attach_wing, orbit_target

WIND_MPS = {"off": 0.0, "low": 1.2, "medium": 3.2, "high": 6.5}


class StudioEngine(ShowBase):
    def __init__(self, width: int = 960, height: int = 540, settings: UserSettings | None = None) -> None:
        cfg = settings or UserSettings()
        apply_panda_prc(cfg, width=width, height=height)
        ShowBase.__init__(self, windowType="offscreen")
        self.disableMouse()
        self.win_w = width
        self.win_h = height
        self.settings = cfg
        self.last_display_rgb = np.zeros((height, width, 3), dtype=np.uint8)
        self.setBackgroundColor(0.45, 0.55, 0.70, 1.0)

        self.color_tex = Texture()
        self.win.addRenderTexture(
            self.color_tex,
            GraphicsOutput.RTMCopyRam,
            GraphicsOutput.RTPColor,
        )

        alight = AmbientLight("alight")
        alight.setColor((0.55, 0.55, 0.6, 1))
        self._alight = alight
        alnp = self.render.attachNewNode(alight)
        self.render.setLight(alnp)
        dlight = DirectionalLight("dlight")
        dlight.setDirection(Vec3(-0.6, -0.8, -1))
        dlight.setColor((0.9, 0.9, 0.85, 1))
        dlnp = self.render.attachNewNode(dlight)
        self.render.setLight(dlnp)

        self.flight_ground = self.render.attachNewNode("flight_ground")
        attach_ground(self.flight_ground)
        self.hangar = attach_hangar(self.render)
        self.hangar.hide()

        self.params = preset("ar_wing")
        self.dynamics = ArcadeDynamics(self.params)
        self.ego = attach_wing(self.render, self.params)
        self.target = attach_target(self.render)
        self.target_phase = 0.0
        self.camera_mode = "nose"  # nose | chase
        self.flight_mode = "MANUAL"
        self.keys: set[str] = set()
        self._last_t = time.perf_counter()
        self.render_fps = 0.0
        self._assist_yaw_fn: Callable[[], float] | None = None
        self.scene_mode = "flight"  # hangar | flight
        self.paused = False
        self.input_enabled = True
        self.target_visible = True
        self.definition: AircraftDefinition | None = None
        self.target_definition: AircraftDefinition | None = None
        self.load_error = ""
        self.target_load_error = ""
        self.preview_heading = 28.0
        self.preview_pitch = 14.0
        self.preview_dist = 8.0
        self.auto_orbit = True
        self._drag = False
        self._drag_last = (0.0, 0.0)
        self.mission_waypoints: list[tuple[float, float, float, float]] = []
        self.mission_i = 0
        self._fail_arm = 0.0
        self._wind_phase = 0.0
        self.chase_yaw = 0.0
        self.chase_pitch = 0.0

        nose = (0.0, 0.35, 0.12)
        self.nose_np = self.ego.attachNewNode("nose_cam_mount")
        self.nose_np.setPos(*nose)

        self.camLens = PerspectiveLens()
        self.camLens.setFov(float(cfg.display.fov))
        self.camLens.setNearFar(0.2, view_distance_far(cfg.graphics.view_distance))
        self.cam.node().setLens(self.camLens)
        apply_texture_quality(cfg.graphics.texture_quality)

    def set_assist_yaw_provider(self, fn: Callable[[], float]) -> None:
        self._assist_yaw_fn = fn

    def apply_graphics(self, settings: UserSettings) -> None:
        self.settings = settings
        self.camLens.setFov(float(settings.display.fov))
        self.camLens.setNearFar(0.2, view_distance_far(settings.graphics.view_distance))
        apply_texture_quality(settings.graphics.texture_quality)

    def resize_buffer(self, width: int, height: int) -> None:
        self.win_w = max(64, int(width))
        self.win_h = max(64, int(height))
        try:
            self.win.setSize(self.win_w, self.win_h)
        except Exception:  # noqa: BLE001
            pass
        self.camLens.setAspectRatio(self.win_w / max(1, self.win_h))

    def set_scene_mode(self, mode: str) -> None:
        self.scene_mode = mode
        if mode == "hangar":
            self.hangar.show()
            self.flight_ground.hide()
            self.target.hide()
            self.setBackgroundColor(0.07, 0.075, 0.08, 1.0)
            self._alight.setColor((0.42, 0.42, 0.44, 1))
            self.auto_orbit = True
            self.preview_heading = 28.0
            self.preview_pitch = 14.0
            if self.definition is not None:
                self.preview_dist = float(self.definition.camera.chase_distance)
        else:
            self.hangar.hide()
            self.flight_ground.show()
            if self.target_visible:
                self.target.show()
            self.setBackgroundColor(0.45, 0.55, 0.70, 1.0)
            self._alight.setColor((0.55, 0.55, 0.6, 1))

    def apply_definition(self, defn: AircraftDefinition) -> str:
        pos = self.dynamics.position()
        hpr = self.dynamics.hpr()
        thr = self.dynamics.state.throttle
        spd = self.dynamics.state.speed
        self.ego.removeNode()
        self.definition = defn
        self.params = to_wing_params(defn)
        self.dynamics.set_params(self.params)
        self.dynamics.state.x, self.dynamics.state.y, self.dynamics.state.z = pos
        self.dynamics.state.yaw_deg, self.dynamics.state.pitch_deg, self.dynamics.state.roll_deg = hpr
        self.dynamics.state.throttle = thr
        self.dynamics.state.speed = spd
        self.ego, err = load_visual(self.loader, self.render, defn)
        self.load_error = err
        nx, ny, nz = defn.camera.nose_offset
        self.nose_np = self.ego.attachNewNode("nose_cam_mount")
        self.nose_np.setPos(nx, ny, nz)
        self.preview_dist = float(defn.camera.chase_distance)
        return err

    def apply_target_definition(self, defn: AircraftDefinition | None) -> str:
        pos = self.target.getPos()
        hpr = self.target.getHpr()
        self.target.removeNode()
        self.target_definition = defn
        if defn is None:
            self.target = attach_target(self.render)
            self.target_load_error = ""
        else:
            self.target, err = load_visual(self.loader, self.render, defn)
            self.target_load_error = err
            self.target.setScale(self.target.getScale()[0] * 0.85)
        self.target.setPos(pos)
        self.target.setHpr(hpr)
        if self.scene_mode == "hangar" or not self.target_visible:
            self.target.hide()
        return self.target_load_error

    def set_aircraft(self, key: str) -> None:
        from .aircraft.registry import AircraftRegistry

        reg = getattr(self, "_registry", None)
        if isinstance(reg, AircraftRegistry):
            defn = reg.get(key)
            if defn is not None:
                self.apply_definition(defn)
                return
        pos = self.dynamics.position()
        hpr = self.dynamics.hpr()
        thr = self.dynamics.state.throttle
        spd = self.dynamics.state.speed
        self.ego.removeNode()
        self.params = preset(key)
        self.dynamics.set_params(self.params)
        self.dynamics.state.x, self.dynamics.state.y, self.dynamics.state.z = pos
        self.dynamics.state.yaw_deg, self.dynamics.state.pitch_deg, self.dynamics.state.roll_deg = hpr
        self.dynamics.state.throttle = thr
        self.dynamics.state.speed = spd
        self.ego = attach_wing(self.render, self.params)
        self.nose_np = self.ego.attachNewNode("nose_cam_mount")
        self.nose_np.setPos(0, 0, 0.12)

    def reset_ego(self) -> None:
        self.dynamics.reset()
        self.mission_i = 0

    def launch(self) -> None:
        self.dynamics.reset()
        self.dynamics.state.throttle = 1.0
        self.dynamics.state.speed = max(14.0, self.params.max_speed * 0.45)
        self.dynamics.state.z = 16.0
        self.mission_i = 0

    def reset_target(self) -> None:
        self.target_phase = 0.0

    def _wind_xy(self, dt: float) -> tuple[float, float]:
        level = (self.settings.simulation.wind or "low").lower()
        mag = WIND_MPS.get(level, 1.2)
        if mag <= 0.0:
            return (0.0, 0.0)
        self._wind_phase += dt * 0.15
        return (mag * math.sin(self._wind_phase), mag * 0.35 * math.cos(self._wind_phase * 0.7))

    def _failing(self, dt: float) -> bool:
        if not self.settings.simulation.failures:
            return False
        self._fail_arm += dt
        return int(self._fail_arm) % 17 >= 14

    def _mission_yaw(self) -> float:
        if not self.mission_waypoints:
            return 0.0
        wp = self.mission_waypoints[self.mission_i % len(self.mission_waypoints)]
        ex, ey, _ez = self.dynamics.position()
        dx, dy = wp[0] - ex, wp[1] - ey
        dist = math.hypot(dx, dy)
        if dist < wp[3]:
            self.mission_i = (self.mission_i + 1) % len(self.mission_waypoints)
        desired = math.degrees(math.atan2(dx, dy))
        err = (desired - self.dynamics.state.yaw_deg + 180.0) % 360.0 - 180.0
        return float(np.clip(err / 45.0, -1.0, 1.0))

    def step_world(self) -> np.ndarray:
        now = time.perf_counter()
        dt = now - self._last_t
        self._last_t = now
        self.render_fps = 1.0 / dt if dt > 1e-6 else 0.0
        if self.scene_mode == "hangar":
            return self._step_hangar(dt)
        if not self.paused:
            self._step_flight(dt)
        else:
            self._apply_flight_camera()
        self.taskMgr.step()
        self.last_display_rgb = self._grab_rgb()
        return self.last_display_rgb

    def _step_hangar(self, dt: float) -> np.ndarray:
        if self.auto_orbit and not self._drag:
            self.preview_heading += dt * 10.0
        self.ego.setPos(0, 0, 1.15)
        self.ego.setHpr(0, 0, 0)
        h = math.radians(self.preview_heading)
        p = math.radians(self.preview_pitch)
        dist = self.preview_dist
        cx = dist * math.sin(h) * math.cos(p)
        cy = -dist * math.cos(h) * math.cos(p)
        cz = 1.15 + dist * math.sin(p)
        self.camera.reparentTo(self.render)
        self.camera.setPos(cx, cy, max(0.4, cz))
        self.camera.lookAt(0, 0, 1.15)
        self.taskMgr.step()
        self.last_display_rgb = self._grab_rgb()
        return self.last_display_rgb

    def _step_flight(self, dt: float) -> None:
        invert = -1.0 if self.settings.controls.invert_y else 1.0
        pitch = float(("s" in self.keys) - ("w" in self.keys)) * invert
        roll = float(("d" in self.keys) - ("a" in self.keys))
        yaw = float(("e" in self.keys) - ("q" in self.keys))
        thr = float(
            (("shift" in self.keys) or ("shift_l" in self.keys) or ("shift_r" in self.keys))
            - (("control" in self.keys) or ("control_l" in self.keys) or ("control_r" in self.keys))
        )
        if not self.input_enabled:
            pitch = roll = yaw = thr = 0.0
        assist = 0.0
        mode = self.flight_mode
        if mode == "FOLLOW":
            mode = "PURSUIT"
        if self._assist_yaw_fn is not None and mode != "MANUAL":
            assist = self._assist_yaw_fn()
            if mode == "ASSIST":
                assist *= 0.55
        if mode == "MISSION":
            assist = self._mission_yaw()
        self.dynamics.step(
            dt,
            pitch_cmd=pitch,
            roll_cmd=roll,
            yaw_cmd=yaw,
            throttle_cmd=thr,
            assist_yaw=assist,
            wind_xy=self._wind_xy(dt),
            sim_speed=float(self.settings.simulation.speed),
            ground_collision=bool(self.settings.simulation.ground_collision),
            difficulty=self.settings.simulation.difficulty,
            fail_throttle=self._failing(dt),
        )
        x, y, z = self.dynamics.position()
        h, p, r = self.dynamics.hpr()
        self.ego.setPos(x, y, z)
        self.ego.setHpr(h, p, r)
        if self.target_visible:
            self.target.show()
            self.target_phase += dt * 0.35
            orbit_target(self.target, self.target_phase, behaviour=self.settings.simulation.target_behaviour)
        else:
            self.target.hide()
        self._apply_flight_camera()

    def _apply_flight_camera(self) -> None:
        cam = self.definition.camera if self.definition is not None else None
        dist = cam.chase_distance if cam else 6.5
        height = cam.chase_height if cam else 2.2
        if self.camera_mode == "nose":
            self.camera.reparentTo(self.nose_np)
            self.camera.setPos(0, 0, 0)
            self.camera.setHpr(0, 0, 0)
            return
        self.camera.reparentTo(self.ego)
        extra = self.chase_yaw
        self.camera.setPos(
            math.sin(math.radians(extra)) * dist,
            -dist * math.cos(math.radians(extra)),
            height + self.chase_pitch,
        )
        self.camera.lookAt(self.ego, Vec3(0, 4, 0))

    def sample_cerber_bgr(self) -> np.ndarray:
        """Nose-camera BGR for CERBER without advancing dynamics."""
        if self.camera_mode == "nose" and hasattr(self, "last_display_rgb"):
            return self.last_display_rgb[:, :, ::-1].copy()
        self.camera.reparentTo(self.nose_np)
        self.camera.setPos(0, 0, 0)
        self.camera.setHpr(0, 0, 0)
        self.graphicsEngine.renderFrame()
        self.graphicsEngine.renderFrame()
        rgb = self._grab_rgb()
        return rgb[:, :, ::-1].copy()

    def _grab_rgb(self) -> np.ndarray:
        if not self.color_tex.hasRamImage():
            return np.zeros((self.win_h, self.win_w, 3), dtype=np.uint8)
        data = self.color_tex.getRamImageAs("RGB")
        arr = np.frombuffer(data, dtype=np.uint8)
        w = self.color_tex.getXSize()
        h = self.color_tex.getYSize()
        if arr.size < w * h * 3:
            return np.zeros((self.win_h, self.win_w, 3), dtype=np.uint8)
        img = arr.reshape((h, w, 3))
        return np.flipud(img).copy()

    def target_distance(self) -> float:
        ex, ey, ez = self.dynamics.position()
        tx, ty, tz = self.target.getPos()
        return float(np.linalg.norm([tx - ex, ty - ey, tz - ez]))

    def yaw_assist_to_target(self) -> float:
        ex, ey, _ez = self.dynamics.position()
        tx, ty, _tz = self.target.getPos()
        dx, dy = tx - ex, ty - ey
        desired = math.degrees(math.atan2(dx, dy))
        err = (desired - self.dynamics.state.yaw_deg + 180.0) % 360.0 - 180.0
        return float(np.clip(err / 45.0, -1.0, 1.0))

    def hangar_drag(self, dx: float, dy: float, sensitivity: float) -> None:
        self.auto_orbit = False
        self.preview_heading -= dx * 0.35 * sensitivity
        self.preview_pitch = float(np.clip(self.preview_pitch + dy * 0.25 * sensitivity, -8.0, 72.0))

    def hangar_zoom(self, delta: float) -> None:
        self.preview_dist = float(np.clip(self.preview_dist * (0.9 if delta > 0 else 1.1), 2.5, 24.0))

    def reset_preview(self) -> None:
        self.auto_orbit = True
        self.preview_heading = 28.0
        self.preview_pitch = 14.0
        if self.definition is not None:
            self.preview_dist = float(self.definition.camera.chase_distance)
        else:
            self.preview_dist = 8.0

    def close_engine(self) -> None:
        ShowBase.destroy(self)


class ViewportWidget(QWidget):
    log_line = Signal(str)

    def __init__(self, parent=None, *, buffer_size: tuple[int, int] = (960, 540), settings: UserSettings | None = None) -> None:
        super().__init__(parent)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.label = QLabel(self)
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setStyleSheet("background:#111;")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self.label)
        self.engine = StudioEngine(width=buffer_size[0], height=buffer_size[1], settings=settings)
        self.engine.set_assist_yaw_provider(self.engine.yaw_assist_to_target)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(16)
        self._frame_cb: Callable[[np.ndarray], None] | None = None
        self._frame_every = 3
        self._frame_i = 0
        self.last_rgb: np.ndarray | None = None
        self._bindings = dict(DEFAULT_BINDINGS)
        self._overlay_fn: Callable[[np.ndarray], np.ndarray] | None = None

    def set_overlay_fn(self, fn: Callable[[np.ndarray], np.ndarray] | None) -> None:
        self._overlay_fn = fn

    def set_frame_callback(self, cb: Callable[[np.ndarray], None] | None, every: int = 3) -> None:
        self._frame_cb = cb
        self._frame_every = max(1, every)

    def set_timer_interval(self, ms: int) -> None:
        self._timer.start(max(1, int(ms)))

    def apply_settings(self, settings: UserSettings) -> None:
        self.engine.settings = settings
        self.engine.apply_graphics(settings)
        self._bindings = dict(DEFAULT_BINDINGS)
        self._bindings.update(settings.controls.bindings or {})

    def _tick(self) -> None:
        rgb = self.engine.step_world()
        if self._overlay_fn is not None:
            rgb = self._overlay_fn(rgb)
        self.last_rgb = rgb
        h, w, _ = rgb.shape
        qimg = QImage(rgb.data, w, h, 3 * w, QImage.Format_RGB888).copy()
        self.label.setPixmap(
            QPixmap.fromImage(qimg).scaled(
                self.label.size(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation,
            )
        )
        self._frame_i += 1
        if (
            self._frame_cb is not None
            and self.engine.scene_mode == "flight"
            and not self.engine.paused
            and self._frame_i % self._frame_every == 0
        ):
            self._frame_cb(self.engine.sample_cerber_bgr())

    def keyPressEvent(self, event: QKeyEvent) -> None:
        mapping = {
            Qt.Key_W: "w",
            Qt.Key_S: "s",
            Qt.Key_A: "a",
            Qt.Key_D: "d",
            Qt.Key_Q: "q",
            Qt.Key_E: "e",
            Qt.Key_Shift: "shift",
            Qt.Key_Control: "control",
        }
        if event.key() in mapping:
            self._map_key(event, True)
            event.accept()
            return
        event.ignore()

    def keyReleaseEvent(self, event: QKeyEvent) -> None:
        mapping = {
            Qt.Key_W: "w",
            Qt.Key_S: "s",
            Qt.Key_A: "a",
            Qt.Key_D: "d",
            Qt.Key_Q: "q",
            Qt.Key_E: "e",
            Qt.Key_Shift: "shift",
            Qt.Key_Control: "control",
        }
        if event.key() in mapping:
            self._map_key(event, False)
            event.accept()
            return
        event.ignore()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.LeftButton and self.engine.scene_mode == "hangar":
            self.engine._drag = True
            self.engine._drag_last = (event.position().x(), event.position().y())
        elif event.button() == Qt.RightButton and self.engine.scene_mode == "flight":
            self.engine._drag = True
            self.engine._drag_last = (event.position().x(), event.position().y())
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self.engine._drag:
            x, y = event.position().x(), event.position().y()
            dx = x - self.engine._drag_last[0]
            dy = y - self.engine._drag_last[1]
            self.engine._drag_last = (x, y)
            sens = float(self.engine.settings.controls.camera_sensitivity)
            if self.engine.scene_mode == "hangar":
                self.engine.hangar_drag(dx, dy, sens)
            else:
                self.engine.chase_yaw += dx * 0.12 * sens
                self.engine.chase_pitch = float(
                    np.clip(self.engine.chase_pitch + dy * 0.02 * sens, -1.5, 3.0)
                )
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        self.engine._drag = False
        super().mouseReleaseEvent(event)

    def wheelEvent(self, event: QWheelEvent) -> None:
        if self.engine.scene_mode == "hangar":
            self.engine.hangar_zoom(event.angleDelta().y())
        event.accept()

    def _map_key(self, event: QKeyEvent, pressed: bool) -> None:
        mapping = {
            Qt.Key_W: "w",
            Qt.Key_S: "s",
            Qt.Key_A: "a",
            Qt.Key_D: "d",
            Qt.Key_Q: "q",
            Qt.Key_E: "e",
            Qt.Key_Shift: "shift",
            Qt.Key_Control: "control",
        }
        name = mapping.get(event.key())
        if name is None:
            return
        if pressed:
            self.engine.keys.add(name)
        else:
            self.engine.keys.discard(name)
