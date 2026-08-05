"""Panda3D offscreen engine painted into a Qt widget."""

from __future__ import annotations

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
    loadPrcFileData,
)
from PySide6.QtCore import Qt, QTimer, Signal
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

from .dynamics import ArcadeDynamics, preset
from .world import attach_ground, attach_target, attach_wing, orbit_target


class StudioEngine(ShowBase):
    def __init__(self, width: int = 960, height: int = 540) -> None:
        loadPrcFileData("", f"win-size {int(width)} {int(height)}")
        ShowBase.__init__(self, windowType="offscreen")
        self.disableMouse()
        self.win_w = width
        self.win_h = height
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
        alnp = self.render.attachNewNode(alight)
        self.render.setLight(alnp)
        dlight = DirectionalLight("dlight")
        dlight.setDirection(Vec3(-0.6, -0.8, -1))
        dlight.setColor((0.9, 0.9, 0.85, 1))
        dlnp = self.render.attachNewNode(dlight)
        self.render.setLight(dlnp)

        attach_ground(self.render)
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

        # nose mount for CERBER sampling
        self.nose_np = self.ego.attachNewNode("nose_cam_mount")
        self.nose_np.setPos(0, 0.35, 0.12)

        self.camLens = PerspectiveLens()
        self.camLens.setFov(75)
        self.camLens.setNearFar(0.2, 2000)
        self.cam.node().setLens(self.camLens)

    def set_assist_yaw_provider(self, fn: Callable[[], float]) -> None:
        self._assist_yaw_fn = fn

    def set_aircraft(self, key: str) -> None:
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
        self.nose_np.setPos(0, 0.35, 0.12)

    def reset_ego(self) -> None:
        self.dynamics.reset()

    def reset_target(self) -> None:
        self.target_phase = 0.0

    def step_world(self) -> np.ndarray:
        now = time.perf_counter()
        dt = now - self._last_t
        self._last_t = now
        self.render_fps = 1.0 / dt if dt > 1e-6 else 0.0

        pitch = float(("s" in self.keys) - ("w" in self.keys))
        roll = float(("d" in self.keys) - ("a" in self.keys))
        yaw = float(("e" in self.keys) - ("q" in self.keys))
        thr = float(
            (("shift" in self.keys) or ("shift_l" in self.keys) or ("shift_r" in self.keys))
            - (("control" in self.keys) or ("control_l" in self.keys) or ("control_r" in self.keys))
        )
        assist = 0.0
        if self._assist_yaw_fn is not None and self.flight_mode != "MANUAL":
            assist = self._assist_yaw_fn()
            if self.flight_mode == "ASSIST":
                assist *= 0.55

        self.dynamics.step(
            dt,
            pitch_cmd=pitch,
            roll_cmd=roll,
            yaw_cmd=yaw,
            throttle_cmd=thr,
            assist_yaw=assist,
        )
        x, y, z = self.dynamics.position()
        h, p, r = self.dynamics.hpr()
        self.ego.setPos(x, y, z)
        self.ego.setHpr(h, p, r)

        self.target_phase += dt * 0.35
        orbit_target(self.target, self.target_phase)

        if self.camera_mode == "nose":
            self.camera.reparentTo(self.nose_np)
            self.camera.setPos(0, 0, 0)
            self.camera.setHpr(0, 0, 0)
        else:
            self.camera.reparentTo(self.ego)
            self.camera.setPos(0, -6.5, 2.2)
            self.camera.lookAt(self.ego, Vec3(0, 4, 0))

        self.taskMgr.step()
        self.last_display_rgb = self._grab_rgb()
        return self.last_display_rgb

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
        desired = math_degrees_atan2(dx, dy)
        err = (desired - self.dynamics.state.yaw_deg + 180.0) % 360.0 - 180.0
        return float(np.clip(err / 45.0, -1.0, 1.0))

    def close_engine(self) -> None:
        ShowBase.destroy(self)


def math_degrees_atan2(dx: float, dy: float) -> float:
    import math

    return math.degrees(math.atan2(dx, dy))


class ViewportWidget(QWidget):
    log_line = Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.label = QLabel(self)
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setStyleSheet("background:#111;")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self.label)
        self.engine = StudioEngine()
        self.engine.set_assist_yaw_provider(self.engine.yaw_assist_to_target)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(16)
        self._frame_cb: Callable[[np.ndarray], None] | None = None
        self._frame_every = 3
        self._frame_i = 0
        self.last_rgb: np.ndarray | None = None

    def set_frame_callback(self, cb: Callable[[np.ndarray], None] | None, every: int = 3) -> None:
        self._frame_cb = cb
        self._frame_every = max(1, every)

    def _tick(self) -> None:
        rgb = self.engine.step_world()
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
        if self._frame_cb is not None and self._frame_i % self._frame_every == 0:
            self._frame_cb(self.engine.sample_cerber_bgr())

    def keyPressEvent(self, event: QKeyEvent) -> None:
        self._map_key(event, True)
        super().keyPressEvent(event)

    def keyReleaseEvent(self, event: QKeyEvent) -> None:
        self._map_key(event, False)
        super().keyReleaseEvent(event)

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
