"""CERBER Lab main loop — Ursina arcade flyer + CERBER PiP."""

from __future__ import annotations

import math
import tempfile
from pathlib import Path

import cv2
import numpy as np
from ursina import (
    AmbientLight,
    DirectionalLight,
    Entity,
    Sky,
    Text,
    Ursina,
    Vec3,
    camera,
    color,
    held_keys,
    invoke,
    window,
)

from .cerber_bridge import CerberBridge
from .dynamics import ArcadeFlyer
from .wings import PRESETS, spawn_target, spawn_wing


MODES = ("MANUAL", "ASSIST", "PURSUIT")


class CerberLabApp:
    def __init__(self, wing_key: str = "ar_wing", enable_cerber: bool = False) -> None:
        if wing_key not in PRESETS:
            wing_key = "ar_wing"
        self.preset = PRESETS[wing_key]
        self.enable_cerber_flag = enable_cerber
        self.mode_i = 0
        self.cerber_on = False
        self.frame_i = 0
        self.last_boxes = []
        self.cerber = CerberBridge("detector_alpha_v2.yaml")
        self._pip_path = Path(tempfile.gettempdir()) / "cerber_lab_pip.png"
        self.app = Ursina(
            title=f"NULLXES CERBER Lab · {self.preset.title}",
            borderless=False,
            fullscreen=False,
            development_mode=False,
            vsync=True,
        )
        window.color = color.rgb(0.08, 0.09, 0.11)
        window.fps_counter.enabled = True
        self._build_world()
        self._build_actors()
        self._build_hud()
        if enable_cerber:
            st = self.cerber.try_load()
            self.cerber_on = st.ok
            self.hud_cerber.text = (
                f"CERBER: READY ({st.detail})" if st.ok else f"CERBER: {st.detail}"
            )
        else:
            self.hud_cerber.text = "CERBER: off (run with --cerber)"

        self.app.update = self._update
        self.app.input = self._input

    def _build_world(self) -> None:
        Sky(color=color.rgb(0.45, 0.55, 0.7))
        DirectionalLight(direction=(0.6, -1, 0.4), shadows=False)
        AmbientLight(color=color.rgba(0.55, 0.55, 0.6, 1))
        # ground grid
        Entity(
            model="plane",
            scale=400,
            color=color.rgb(0.18, 0.22, 0.16),
            texture="white_cube",
            texture_scale=(80, 80),
            collider="box",
            position=(0, 0, 0),
        )
        # runway strip
        Entity(
            model="cube",
            scale=(12, 0.05, 120),
            color=color.rgb(0.25, 0.25, 0.28),
            position=(0, 0.03, 40),
        )

    def _build_actors(self) -> None:
        self.ego = spawn_wing(self.preset, Vec3(0, 14, 0))
        self.flyer = ArcadeFlyer(self.ego, self.preset)
        self.target = spawn_target(Vec3(30, 20, 55))
        self._target_phase = 0.0
        camera.parent = self.ego
        camera.position = Vec3(0, 0.35, 0.2)
        camera.rotation = Vec3(0, 0, 0)
        camera.fov = 75

    def _build_hud(self) -> None:
        tip = (
            "WASD pitch/roll · QE yaw · Shift/Ctrl throttle · "
            "F1 target · C CERBER · 1/2/3 mode · R reset · Esc quit"
        )
        Text(
            text=tip,
            parent=camera.ui,
            position=(-0.85, -0.45),
            scale=0.7,
            color=color.rgb(0.85, 0.85, 0.85),
            origin=(-0.5, 0),
        )
        self.hud_title = Text(
            text=f"NULLXES CERBER Lab · {self.preset.title}",
            parent=camera.ui,
            position=(-0.85, 0.45),
            scale=1.0,
            color=color.rgb(0.95, 0.35, 0.35),
            origin=(-0.5, 0),
        )
        self.hud_mode = Text(
            text="MODE: MANUAL",
            parent=camera.ui,
            position=(-0.85, 0.40),
            scale=0.9,
            color=color.azure,
            origin=(-0.5, 0),
        )
        self.hud_telem = Text(
            text="",
            parent=camera.ui,
            position=(-0.85, 0.35),
            scale=0.75,
            color=color.white,
            origin=(-0.5, 0),
        )
        self.hud_cerber = Text(
            text="",
            parent=camera.ui,
            position=(-0.85, 0.30),
            scale=0.7,
            color=color.lime,
            origin=(-0.5, 0),
        )
        self.hud_banner = Text(
            text="ARCADE VIZ · NOT DIGITAL TWIN",
            parent=camera.ui,
            position=(0.35, 0.45),
            scale=0.7,
            color=color.orange,
            origin=(-0.5, 0),
        )
        # PiP panel
        self.pip = Entity(
            parent=camera.ui,
            model="quad",
            scale=(0.42, 0.28),
            position=(0.62, -0.28),
            color=color.black,
            z=-0.1,
        )
        self.pip_label = Text(
            text="CERBER EYE",
            parent=camera.ui,
            position=(0.42, -0.10),
            scale=0.65,
            color=color.rgb(0.7, 0.9, 0.7),
            origin=(-0.5, 0),
        )

    def _input(self, key: str) -> None:
        if key == "escape":
            self.app.quit()
        if key == "r":
            self.flyer.reset(Vec3(0, 14, 0))
        if key == "f1":
            self._target_phase = 0.0
            self.target.position = Vec3(30, 20, 55)
        if key == "c":
            if not self.cerber.status.ok:
                st = self.cerber.try_load()
                self.hud_cerber.text = (
                    f"CERBER: READY ({st.detail})" if st.ok else f"CERBER: {st.detail}"
                )
            self.cerber_on = bool(self.cerber.status.ok) and (not self.cerber_on)
        if key in ("1", "2", "3"):
            self.mode_i = int(key) - 1
            self.hud_mode.text = f"MODE: {MODES[self.mode_i]}"

    def _move_target(self) -> None:
        self._target_phase += time_dt() * 0.35
        r = 28.0
        self.target.x = 20 + r * math.cos(self._target_phase)
        self.target.z = 50 + r * math.sin(self._target_phase)
        self.target.y = 18 + 3 * math.sin(self._target_phase * 2)
        self.target.look_at(self.target.position + Vec3(-math.sin(self._target_phase), 0, math.cos(self._target_phase)))

    def _assist_yaw(self) -> float:
        mode = MODES[self.mode_i]
        if mode == "MANUAL":
            return 0.0
        # point nose toward target (world)
        to = self.target.world_position - self.ego.world_position
        if to.length() < 1e-3:
            return 0.0
        to = to.normalized()
        flat_fwd = Vec3(self.ego.forward.x, 0, self.ego.forward.z)
        flat_to = Vec3(to.x, 0, to.z)
        if flat_fwd.length() < 1e-3 or flat_to.length() < 1e-3:
            return 0.0
        flat_fwd = flat_fwd.normalized()
        flat_to = flat_to.normalized()
        cross = flat_fwd.x * flat_to.z - flat_fwd.z * flat_to.x
        # desire yaw rate command in [-1,1]
        gain = 0.55 if mode == "ASSIST" else 1.0
        # if CERBER on and no uav box, weaken pursuit
        if self.cerber_on and mode == "PURSUIT":
            uav = [b for b in self.last_boxes if b.name == "uav"]
            if not uav:
                gain *= 0.15
        return max(-1.0, min(1.0, cross * 3.0 * gain))

    def _grab_bgr(self) -> np.ndarray | None:
        """Screenshot nose view → BGR for CERBER."""
        try:
            from panda3d.core import Filename, PNMImage
            from ursina import application

            img = PNMImage()
            application.base.win.getScreenshot(img)
            tmp = Filename.from_os_specific(str(self._pip_path))
            img.write(tmp)
            bgr = cv2.imread(str(self._pip_path), cv2.IMREAD_COLOR)
            return bgr
        except Exception:  # noqa: BLE001
            return None

    def _update_pip(self, bgr: np.ndarray) -> None:
        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        # downscale for UI texture
        rgb = cv2.resize(rgb, (640, 360), interpolation=cv2.INTER_AREA)
        cv2.imwrite(str(self._pip_path), cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR))
        try:
            self.pip.texture = str(self._pip_path)
            self.pip.color = color.white
        except Exception:  # noqa: BLE001
            pass

    def _update(self) -> None:
        self._move_target()
        pitch = float(held_keys["s"] - held_keys["w"])
        roll = float(held_keys["d"] - held_keys["a"])
        yaw = float(held_keys["e"] - held_keys["q"])
        thr = float(
            held_keys["shift"]
            - held_keys["control"]
            - held_keys["left control"]
            - held_keys["right control"]
        )
        self.flyer.update(
            pitch=pitch,
            roll=roll,
            yaw=yaw,
            throttle_delta=thr * 0.6,
            assist_yaw=self._assist_yaw(),
        )
        spd = self.flyer.st.speed
        self.hud_telem.text = (
            f"SPD {spd:4.1f}  ALT {self.ego.y:5.1f}  "
            f"THR {self.flyer.st.throttle:0.2f}  "
            f"TGT dist {(self.target.world_position - self.ego.world_position).length():.0f}m"
        )

        self.frame_i += 1
        if self.cerber_on and self.frame_i % 4 == 0:
            bgr = self._grab_bgr()
            if bgr is not None:
                boxes = self.cerber.infer(bgr)
                self.last_boxes = boxes
                hud = f"CERBER · boxes={len(boxes)} · {MODES[self.mode_i]}"
                drawn = self.cerber.draw(bgr, boxes, hud)
                self._update_pip(drawn)
                uav_n = sum(1 for b in boxes if b.name == "uav")
                self.hud_cerber.text = (
                    f"CERBER: ON · det={len(boxes)} uav={uav_n} · {self.cerber.status.detail}"
                )
        elif not self.cerber_on and self.frame_i % 30 == 0:
            # still refresh PiP raw view occasionally
            bgr = self._grab_bgr()
            if bgr is not None:
                raw = self.cerber.draw(bgr, [], "CERBER EYE · overlay off")
                self._update_pip(raw)

    def run(self) -> None:
        # defer first pip fill
        invoke(self._update, delay=0.05)
        self.app.run()


def time_dt() -> float:
    from ursina import time

    return float(time.dt)


def run_lab(wing: str = "ar_wing", cerber: bool = False) -> None:
    CerberLabApp(wing_key=wing, enable_cerber=cerber).run()
