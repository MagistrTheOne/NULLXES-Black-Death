"""Panda3D offscreen engine painted into a Qt widget."""

from __future__ import annotations

import math
import time
from typing import Callable

import numpy as np
from panda3d.core import (
    AmbientLight,
    DirectionalLight,
    Fog,
    GraphicsOutput,
    PerspectiveLens,
    Texture,
    Vec3,
)
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QImage, QKeyEvent, QMouseEvent, QPixmap, QWheelEvent
from PySide6.QtWidgets import QLabel, QSizePolicy, QVBoxLayout, QWidget

from direct.showbase.ShowBase import ShowBase

from .activity import ActivityDirector
from .aircraft.animation import VisualAnimator
from .aircraft.definition import AircraftDefinition
from .aircraft.loader import frame_distance, load_visual, to_wing_params, visual_radius
from .config.settings import DEFAULT_BINDINGS, UserSettings
from .blackbox.recorder import FlightRecorder, blackbox_root, load_replay
from .debug.profiler import FrameProfiler
from .debug.world_debug import WorldDebugOverlay
from .display import apply_panda_prc, apply_texture_quality, fog_density, view_distance_far
from .dynamics import PHYSICS_DT, FlightPhase, preset
from .input_map import bindings_map
from .sim.metrics import RuntimeMetrics
from .sim.vehicle import ControlInput
from .sim_backend import make_backend
from .training import TrainingState
from .world import attach_hangar, attach_target, attach_wing, orbit_target
from .world_gen import WorldStreamer, apply_atmosphere, apply_lighting, apply_sun, attach_haze, attach_sky
from .world_gen.geom import box
from .world_gen.region_preview import RegionPreview

WIND_MPS = {"off": 0.0, "low": 1.2, "medium": 3.2, "high": 6.5}
CAMERAS = ("chase", "nose", "orbit", "ground", "flyby", "free")


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
        self.setBackgroundColor(0.70, 0.76, 0.82, 1.0)

        self.color_tex = Texture()
        self.win.addRenderTexture(
            self.color_tex,
            GraphicsOutput.RTMCopyRam,
            GraphicsOutput.RTPColor,
        )

        alight = AmbientLight("alight")
        alight.setColor((0.42, 0.45, 0.50, 1))
        self._alight = alight
        alnp = self.render.attachNewNode(alight)
        self.render.setLight(alnp)
        dlight = DirectionalLight("dlight")
        dlight.setDirection(Vec3(-0.45, -0.55, -0.85))
        dlight.setColor((1.0, 0.96, 0.88, 1))
        self._dlight = dlight
        dlnp = self.render.attachNewNode(dlight)
        self.render.setLight(dlnp)
        apply_sun(self.render, alight, dlight)

        self.sky = attach_sky(self.render)
        self._fog: Fog = attach_haze(self.render, fog_density(cfg.graphics.view_distance))
        self.world = WorldStreamer(self.render)
        self.world.set_active(False)
        self.hangar = attach_hangar(self.render)
        self.hangar.hide()
        self.hangar_anchor = self.hangar.find("preview_anchor")
        if self.hangar_anchor.isEmpty():
            self.hangar_anchor = self.hangar.attachNewNode("preview_anchor")
            self.hangar_anchor.setPos(0, 0, 0.22)

        self.params = preset("ar_wing")
        self.dynamics = make_backend(cfg.simulation.backend, self.params)
        self.ego = attach_wing(self.render, self.params)
        self._attach_nav_lights()
        self.target = attach_target(self.render)
        self.target_phase = 0.0
        self.camera_mode = "chase"
        self.flight_mode = "MANUAL"
        self.keys: set[str] = set()
        self.actions: set[str] = set()
        self._last_t = time.perf_counter()
        self.render_fps = 0.0
        self._assist_yaw_fn: Callable[[], float] | None = None
        self.scene_mode = "flight"
        self.runtime_scope = "menu"
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
        self._phys_acc = 0.0
        self._cam_pos = Vec3(0, -12, 4)
        self._fov = float(cfg.display.fov)
        self.training = TrainingState()
        self._pose_prev = (0.0, 0.0, 0.6, 0.0, 0.0, 0.0)
        self._pose_curr = self._pose_prev
        self.blackbox = FlightRecorder()
        self.replay_active = False
        self.replay_poses: list[dict] = []
        self.replay_i = 0
        self._trail: list[tuple[float, float, float]] = []
        self._flyby_i = 0
        self._tod_clock = -1.0
        self.hangar_parked: list = []
        self.hangar_index = 0
        self.hangar_line_active = False
        self.preview_radius = 1.6
        self.animator = VisualAnimator()
        self.profiler = FrameProfiler()
        self.world_debug = WorldDebugOverlay(self.render)
        self.region_preview = RegionPreview(self.render)
        self.debug_perf = False
        self.debug_world = False
        self._world_acc = 0.0
        self._act_acc = 0.0
        self._atmo_acc = 0.0
        self._disc_acc = 0.0
        self._sky_acc = 0.0
        self._cerber_busy = False
        self.operator_tab = False
        self.hud_layer = str(cfg.hud.layer or cfg.hud.preset or "flight")
        self.activity = ActivityDirector(self.render, self.world.graph)
        self.activity.root.hide()
        self.replay_events: list[dict] = []
        self.cinematic = False
        self._fov_restore = float(cfg.display.fov)
        self._mission_wind: str | None = None
        self._mission_assist: bool | None = None
        self._prev_phase = ""
        self._prev_stall = False
        self._prev_overspeed = False
        self._prev_lights = False
        self.discovered_now: list[str] = []
        self.runtime = RuntimeMetrics()
        self.soak_cmd: ControlInput | None = None
        self.replay_warning = ""
        self.blackbox_contract: dict = {}

        nose = (0.0, 0.35, 0.12)
        self.nose_np = self.ego.attachNewNode("nose_cam_mount")
        self.nose_np.setPos(*nose)

        self.camLens = PerspectiveLens()
        self.camLens.setFov(self._fov)
        self.camLens.setNearFar(0.2, view_distance_far(cfg.graphics.view_distance))
        self.cam.node().setLens(self.camLens)
        apply_texture_quality(cfg.graphics.texture_quality)
        self.set_scene_mode("hangar")

    def set_assist_yaw_provider(self, fn: Callable[[], float] | None) -> None:
        self._assist_yaw_fn = fn

    def apply_graphics(self, settings: UserSettings) -> None:
        self.settings = settings
        self.camLens.setFov(float(settings.display.fov))
        self._fov = float(settings.display.fov)
        self.camLens.setNearFar(0.2, view_distance_far(settings.graphics.view_distance))
        apply_texture_quality(settings.graphics.texture_quality)
        dens = fog_density(settings.graphics.view_distance)
        self._fog.setExpDensity(dens)
        dyn = getattr(self.dynamics, "inner", self.dynamics)
        assist = self.settings.simulation.launch_assist if self._mission_assist is None else self._mission_assist
        dyn.set_launch_assist(bool(assist))
        dyn.set_auto_level(settings.simulation.difficulty != "strict")
        dyn._sensitivity = float(settings.controls.sensitivity)

    def resize_buffer(self, width: int, height: int) -> None:
        tex_w = int(self.color_tex.getXSize() or width)
        tex_h = int(self.color_tex.getYSize() or height)
        self.win_w = max(64, tex_w)
        self.win_h = max(64, tex_h)
        self.camLens.setAspectRatio(self.win_w / max(1, self.win_h))

    def set_scene_mode(self, mode: str) -> None:
        if mode == self.scene_mode and mode == "flight":
            return
        self.scene_mode = mode
        if mode == "hangar":
            self.runtime_scope = "menu"
            self.hangar.show()
            self.world.set_active(False)
            self.region_preview.hide()
            self.sky.hide()
            self.target.hide()
            self.setBackgroundColor(0.07, 0.075, 0.08, 1.0)
            self._alight.setColor((0.28, 0.29, 0.31, 1))
            self.render.clearFog()
            self.auto_orbit = True
            self.preview_heading = 28.0
            self.preview_pitch = 12.0
            self.hangar_line_active = False
            self.activity.root.hide()
            self.animator.hangar = True
            self.animator.rpm = 0.0
            self.animator.step(0.0)
            for node in self.hangar_parked:
                node.hide()
            if not self.ego.isEmpty():
                self.ego.wrtReparentTo(self.hangar_anchor)
                self.ego.setPos(0, 0, 0)
                self.ego.setHpr(0, 0, 0)
                self.ego.show()
            self._fit_hangar_camera()
        elif mode == "region":
            self.runtime_scope = "preview"
            self.hangar.hide()
            self.world.set_active(False)
            self.activity.root.hide()
            self.ego.hide()
            self.target.hide()
            self.sky.show()
            self.region_preview.show()
            self.animator.hangar = True
        else:
            self.runtime_scope = "replay" if self.replay_active else "flight"
            self.hangar.hide()
            self.region_preview.hide()
            self.sky.show()
            self.world.set_active(True)
            self.activity.root.show()
            self.render.setFog(self._fog)
            self._apply_sky()
            if self.target_visible:
                self.target.show()
            else:
                self.target.hide()
            self.setBackgroundColor(0.70, 0.76, 0.82, 1.0)
            if not self.ego.isEmpty():
                self.ego.wrtReparentTo(self.render)
                self.ego.show()
            self.animator.hangar = False

    def prepare_world(self) -> None:
        sess = self.settings.session
        self.world.configure(int(sess.world_seed), sess.region_id or "forest")
        preset = sess.weather or self.world.graph.profile.sky_preset or "clear"
        self.world.atmosphere.apply_preset(preset)
        self.world.atmosphere.temperature_c = float(self.world.graph.profile.temperature_c)
        self.world.atmosphere.time_flow = sess.time_flow or "1x"
        self.world.load_packs(self.loader)
        self.world.set_active(True)
        self.activity.rebuild(self.world.graph, self.render)
        self.activity.root.show()
        self.runtime.world_gen_ms = float(self.world.gen_ms)
        sx, sy, _, _ = self.world.spawn()
        self.world.ensure(sx, sy)
        self._apply_sky(rebuild=True)
        self.replay_active = False
        self.replay_poses = []
        self.replay_events = []
        self._trail = []
        self._prev_phase = ""
        self._prev_stall = False
        self._prev_overspeed = False
        self.discovered_now = []

    def _apply_sky(self, rebuild: bool = True) -> None:
        dens = fog_density(self.settings.graphics.view_distance)
        pal = apply_lighting(
            self.render,
            self._alight,
            self._dlight,
            self._fog,
            self.world.atmosphere,
            dens,
        )
        if rebuild:
            self.sky = apply_atmosphere(
                self.render,
                self.sky,
                self._alight,
                self._dlight,
                self._fog,
                self.world.atmosphere,
                dens,
            )
        bg = pal.get("bg", pal.get("haze", (0.70, 0.76, 0.82)))
        self.setBackgroundColor(bg[0], bg[1], bg[2], 1.0 if len(bg) < 4 else bg[3])
        self._tod_clock = float(self.world.atmosphere.clock_h)
        self._prev_lights = self.world.atmosphere.lights_on

    def preview_region(self, region_id: str) -> None:
        self.settings.session.region_id = region_id
        self.world.set_active(False)
        self.activity.root.hide()
        self.hangar.hide()
        self.ego.hide()
        self.target.hide()
        self.sky.show()
        dens = fog_density(self.settings.graphics.view_distance)
        profile = None
        try:
            from .world_gen.world_profile import load_profile

            profile = load_profile(region_id)
            self.world.atmosphere.apply_preset(profile.sky_preset or "clear")
            self.world.atmosphere.temperature_c = float(profile.temperature_c)
        except Exception:
            self.world.atmosphere.apply_preset("clear")
        self.render.setFog(self._fog)
        self._apply_sky(rebuild=True)
        self.region_preview.rebuild(int(self.settings.session.world_seed), region_id, self.loader)
        self.camera.reparentTo(self.render)
        eye, look = self.region_preview.camera_pose(0.0)
        self.camera.setPos(eye)
        self.camera.lookAt(look)
        self.scene_mode = "region"
        self.runtime_scope = "preview"

    def exit_region_preview(self) -> None:
        self.region_preview.hide()
        if self.scene_mode == "region":
            self.set_scene_mode("hangar")

    def apply_definition(self, defn: AircraftDefinition) -> str:
        pos = self.dynamics.position()
        hpr = self.dynamics.hpr()
        thr = self.dynamics.state.throttle
        spd = self.dynamics.state.speed
        phase = self.dynamics.state.phase
        self.ego.removeNode()
        self.definition = defn
        self.params = to_wing_params(defn)
        self.dynamics.set_params(self.params)
        if phase in (FlightPhase.GROUND, FlightPhase.READY, FlightPhase.LANDED) or self.scene_mode == "hangar":
            pass
        else:
            self.dynamics.state.x, self.dynamics.state.y, self.dynamics.state.z = pos
            self.dynamics.state.yaw_deg, self.dynamics.state.pitch_deg, self.dynamics.state.roll_deg = hpr
            self.dynamics.state.throttle = thr
            self.dynamics.control.throttle = thr
            self.dynamics.state.speed = spd
        parent = self.hangar_anchor if self.scene_mode == "hangar" else self.render
        self.ego, err, self.animator = load_visual(self.loader, parent, defn)
        self.load_error = err
        self.animator.hangar = self.scene_mode != "flight"
        nx, ny, nz = defn.camera.nose_offset
        self.nose_np = self.ego.attachNewNode("nose_cam_mount")
        self.nose_np.setPos(nx, ny, nz)
        self._attach_nav_lights()
        if self.scene_mode == "hangar":
            self.ego.setPos(0, 0, 0)
            self.ego.setHpr(0, 0, 0)
            self._fit_hangar_camera()
        else:
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
            self.target, err, _anim = load_visual(self.loader, self.render, defn)
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
        self.ego.removeNode()
        self.params = preset(key)
        self.dynamics.set_params(self.params)
        self.ego = attach_wing(self.render, self.params)
        self.nose_np = self.ego.attachNewNode("nose_cam_mount")
        self.nose_np.setPos(0, 0, 0.12)
        self._attach_nav_lights()

    def spawn_ready(self) -> None:
        sx, sy, gz, yaw = self.world.spawn()
        self.dynamics.reset(x=sx, y=sy, yaw_deg=yaw, ground_z=gz)
        assist = self.settings.simulation.launch_assist if self._mission_assist is None else self._mission_assist
        self.dynamics.set_launch_assist(bool(assist))
        self.mission_i = 0
        self._phys_acc = 0.0
        self.camera_mode = "chase"
        pose = (sx, sy, gz + 0.55, yaw, 0.0, 0.0)
        self._pose_prev = pose
        self._pose_curr = pose
        self._cam_pos = Vec3(sx, sy - 14.0, gz + 3.6)
        self._sync_ego(1.0)

    def reset_ego(self) -> None:
        self.spawn_ready()

    def launch(self) -> bool:
        ok = self.dynamics.request_launch()
        return ok

    def cycle_camera(self) -> None:
        try:
            i = CAMERAS.index(self.camera_mode)
        except ValueError:
            i = 0
        self.camera_mode = CAMERAS[(i + 1) % len(CAMERAS)]
        self.training.mark_camera()

    def reset_target(self) -> None:
        self.target_phase = 0.0

    def _wind_xy(self, dt: float) -> tuple[float, float]:
        level = (self._mission_wind or self.settings.simulation.wind or "low").lower()
        mag = WIND_MPS.get(level, 1.2)
        atmos = self.world.atmosphere
        mag = max(mag, atmos.wind_mps)
        self._wind_phase += dt * 0.15
        base = (mag * math.sin(self._wind_phase), mag * 0.35 * math.cos(self._wind_phase * 0.7))
        g = atmos.gust_mps
        gust = (g * math.sin(self._wind_phase * 4.2), g * 0.45 * math.cos(self._wind_phase * 3.1))
        return (base[0] + gust[0], base[1] + gust[1])

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
        self.profiler.begin_frame()
        if self.scene_mode == "hangar":
            rgb = self._step_hangar(dt)
        elif self.scene_mode == "region":
            rgb = self._step_region(dt)
        elif self.replay_active and not self.paused:
            self.runtime_scope = "replay"
            self._step_replay(dt)
            self.taskMgr.step()
            rgb = self._grab_rgb()
            self.last_display_rgb = rgb
        elif not self.paused:
            self.runtime_scope = "flight"
            self.runtime.begin_frame()
            with self.profiler.span("update"):
                self._step_flight(dt)
            self.runtime.end_frame()
            self._collect_runtime()
            self.taskMgr.step()
            rgb = self._grab_rgb()
            self.last_display_rgb = rgb
        else:
            self.taskMgr.step()
            rgb = self._grab_rgb()
            self.last_display_rgb = rgb
        self.profiler.end_frame(dt=dt)
        if self.debug_perf or self.profiler.enabled:
            st = self.world.stats()
            self.profiler.refresh_snap(
                self.render,
                sectors=int(st["sectors"]),
                props=int(st["props"]),
                entities=sum(self.activity.lod_counts().values()),
            )
        return self.last_display_rgb

    def _step_region(self, dt: float) -> np.ndarray:
        eye, look = self.region_preview.camera_pose(dt)
        self.camera.reparentTo(self.render)
        self.camera.setPos(eye)
        self.camera.lookAt(look)
        self.sky.setPos(eye)
        self.taskMgr.step()
        self.last_display_rgb = self._grab_rgb()
        return self.last_display_rgb

    def _fit_hangar_camera(self) -> None:
        if self.ego.isEmpty():
            return
        self.preview_radius = max(0.4, visual_radius(self.ego))
        aspect = self.win_w / max(1, self.win_h)
        dist = frame_distance(self.preview_radius, self._fov, 0.55, aspect)
        self.preview_dist = float(np.clip(dist, 2.6, 16.0))

    def _step_hangar(self, dt: float) -> np.ndarray:
        if self.auto_orbit and not self._drag:
            self.preview_heading += dt * 10.0
        self.ego.show()
        self.ego.setPos(0, 0, 0)
        self.ego.setHpr(0, 0, 0)
        self.target.hide()
        for node in self.hangar_parked:
            node.hide()
        h = math.radians(self.preview_heading)
        p = math.radians(self.preview_pitch)
        dist = self.preview_dist
        look_z = self.preview_radius * 0.42
        cx = dist * math.sin(h) * math.cos(p)
        cy = -dist * math.cos(h) * math.cos(p)
        cz = look_z + dist * math.sin(p)
        self.camera.reparentTo(self.render)
        ax, ay, az = self.hangar_anchor.getPos(self.render)
        self.camera.setPos(ax + cx, ay + cy, max(az + 0.35, az + cz))
        self.camera.lookAt(ax, ay, az + look_z)
        self.animator.hangar = True
        self.animator.rpm = 0.0
        self.animator.step(dt)
        self.taskMgr.step()
        self.last_display_rgb = self._grab_rgb()
        return self.last_display_rgb

    def _axis(self, plus: str, minus: str) -> float:
        return float((plus in self.actions) - (minus in self.actions))

    def _step_flight(self, dt: float) -> None:
        invert = -1.0 if self.settings.controls.invert_y else 1.0
        pitch = self._axis("pitch_up", "pitch_down") * invert
        roll = self._axis("roll_right", "roll_left")
        yaw = self._axis("yaw_right", "yaw_left")
        thr = self._axis("throttle_up", "throttle_down")
        if self.soak_cmd is not None:
            pitch, roll, yaw, thr = self.soak_cmd.pitch, self.soak_cmd.roll, self.soak_cmd.yaw, self.soak_cmd.throttle
            if self.soak_cmd.mode:
                mode_override = self.soak_cmd.mode
            else:
                mode_override = None
        else:
            mode_override = None
        if not self.input_enabled and self.soak_cmd is None:
            pitch = roll = yaw = thr = 0.0
        assist = 0.0
        mode = mode_override or self.flight_mode
        if mode == "FOLLOW":
            mode = "PURSUIT"
        airborne = self.dynamics.state.phase.value in (
            "LAUNCH",
            "AIRBORNE",
            "FLIGHT",
            "APPROACH",
            "TOUCHDOWN",
        )
        if airborne and self._assist_yaw_fn is not None and mode != "MANUAL":
            assist = self._assist_yaw_fn()
            if mode == "ASSIST":
                assist *= 0.55
        if airborne and mode == "MISSION":
            assist = self._mission_yaw()

        self._phys_acc += min(0.08, dt)
        steps = 0
        graph = self.world.graph
        af = graph.airfields[0] if graph.airfields else None
        runway_yaw = af.yaw if af is not None else 0.0
        t_phys = time.perf_counter()
        while self._phys_acc >= PHYSICS_DT and steps < 8:
            self._pose_prev = self._pose_curr
            gz = self.world.ground_z(self.dynamics.state.x, self.dynamics.state.y)
            on_rw = graph.airfield_mask(self.dynamics.state.x, self.dynamics.state.y)
            self.dynamics.step(
                PHYSICS_DT,
                pitch_cmd=pitch,
                roll_cmd=roll,
                yaw_cmd=yaw,
                throttle_cmd=thr,
                assist_yaw=assist,
                wind_xy=self._wind_xy(PHYSICS_DT),
                sim_speed=float(self.settings.simulation.speed),
                ground_collision=bool(self.settings.simulation.ground_collision),
                difficulty=self.settings.simulation.difficulty,
                fail_throttle=self._failing(PHYSICS_DT),
                ground_z=gz,
                on_runway=on_rw,
                runway_yaw=runway_yaw,
                flight_mode=mode,
            )
            s = self.dynamics.state
            self._pose_curr = (s.x, s.y, s.z, s.yaw_deg, s.pitch_deg, s.roll_deg)
            self._phys_acc -= PHYSICS_DT
            steps += 1
            self.runtime.phys_steps += 1
            self._trail.append((s.x, s.y, s.z))
            if len(self._trail) > 240:
                self._trail = self._trail[-240:]
        if self._phys_acc >= PHYSICS_DT:
            self.runtime.phys_misses += 1
            self._phys_acc = 0.0
        self.profiler.add_ms("physics", (time.perf_counter() - t_phys) * 1000.0)

        self._atmo_acc += dt
        if self._atmo_acc >= 0.12:
            self.world.atmosphere.step_clock(self._atmo_acc)
            clock = self.world.atmosphere.clock_h
            rebuild = abs(clock - self._tod_clock) >= 0.55
            t_at = time.perf_counter()
            self._apply_sky(rebuild=rebuild)
            self.profiler.add_ms("atmosphere", (time.perf_counter() - t_at) * 1000.0)
            self._atmo_acc = 0.0

        alpha = float(np.clip(1.0 - (self._phys_acc / PHYSICS_DT), 0.0, 1.0))
        self._sync_ego(alpha)
        self.animator.hangar = False
        self.animator.set_throttle(float(self.dynamics.state.throttle))
        self.animator.step(dt)
        if self.target_visible:
            self.target.show()
            self.target_phase += dt * 0.35
            orbit_target(self.target, self.target_phase, behaviour=self.settings.simulation.target_behaviour)
        else:
            self.target.hide()
        x, y, z = self.dynamics.position()
        self._world_acc += dt
        if self._world_acc >= 0.05:
            t_w = time.perf_counter()
            self.world.update(x, y, z)
            self.profiler.add_ms("world", (time.perf_counter() - t_w) * 1000.0)
            self._world_acc = 0.0
        self._act_acc += dt
        if self._act_acc >= 0.04:
            t_a = time.perf_counter()
            self.activity.update(self._act_acc, (x, y), self.world.ground_z)
            self.profiler.add_ms("activity", (time.perf_counter() - t_a) * 1000.0)
            self._act_acc = 0.0
        self._sync_nav_lights()
        self._emit_flight_events()
        self._disc_acc += dt
        if self._disc_acc >= 0.25:
            self._scan_landmarks()
            self._disc_acc = 0.0
        self.training.update(
            phase=self.dynamics.state.phase,
            throttle=self.dynamics.state.throttle,
            pitch_in=self.dynamics.control.pitch,
            roll_deg=self.dynamics.state.roll_deg,
            yaw_deg=self.dynamics.state.yaw_deg,
            agl=self.dynamics.state.agl,
        )
        self._apply_flight_camera(dt)

    def _sync_ego(self, alpha: float) -> None:
        a = float(np.clip(alpha, 0.0, 1.0))
        p0, p1 = self._pose_prev, self._pose_curr

        def lerp(i: int) -> float:
            return p0[i] + (p1[i] - p0[i]) * a

        def lerp_ang(i: int) -> float:
            d = (p1[i] - p0[i] + 180.0) % 360.0 - 180.0
            return (p0[i] + d * a) % 360.0

        x, y, z = lerp(0), lerp(1), lerp(2)
        h, p, r = lerp_ang(3), p0[4] + (p1[4] - p0[4]) * a, p0[5] + (p1[5] - p0[5]) * a
        self.ego.setPos(x, y, z)
        self.ego.setHpr(h, p, r)

    def _apply_flight_camera(self, dt: float = 0.016) -> None:
        cam = self.definition.camera if self.definition is not None else None
        base_dist = cam.chase_distance if cam else 8.0
        height = cam.chase_height if cam else 2.2
        x, y, z = self.ego.getPos()
        yaw = self.ego.getH()
        speed = self.dynamics.state.speed
        target_fov = float(self.settings.display.fov) + min(10.0, speed * 0.16)
        self._fov += (target_fov - self._fov) * min(1.0, 2.2 * dt)
        self.camLens.setFov(self._fov)

        if self.camera_mode == "nose":
            self.camera.reparentTo(self.nose_np)
            self.camera.setPos(0, 0, 0)
            self.camera.setHpr(0, 0, 0)
            return

        yr = math.radians(yaw)
        forward = Vec3(math.sin(yr), math.cos(yr), 0)
        self.camera.reparentTo(self.render)
        if self.camera_mode == "free" or self.cinematic:
            dist = base_dist + 4.0
            fy = math.radians(self.chase_yaw + yaw)
            fp = math.radians(12.0 + self.chase_pitch * 12.0)
            desired = Vec3(
                x + math.sin(fy) * dist * math.cos(fp),
                y - math.cos(fy) * dist * math.cos(fp),
                z + dist * math.sin(fp) + 1.5,
            )
        elif self.camera_mode == "orbit":
            ang = time.perf_counter() * 0.25
            dist = base_dist + 6.0
            desired = Vec3(x + math.sin(ang) * dist, y - math.cos(ang) * dist, z + height + 4.0)
        elif self.camera_mode == "ground":
            desired = Vec3(x - math.sin(yr) * 18.0, y - math.cos(yr) * 18.0, self.world.ground_z(x, y) + 1.8)
        elif self.camera_mode == "flyby":
            look_i = max(0, len(self._trail) - 8)
            if self.replay_poses:
                look_i = min(len(self.replay_poses) - 1, self.replay_i + 18)
                sp = self.replay_poses[look_i]
                desired = Vec3(sp["x"] + 12.0, sp["y"] - 4.0, sp["z"] + 2.0)
            elif self._trail:
                px, py, pz = self._trail[look_i]
                desired = Vec3(px + math.cos(yr) * 14.0, py - math.sin(yr) * 8.0, pz + 2.5)
            else:
                desired = Vec3(x + math.cos(yr) * 16.0, y - 8.0, z + 2.0)
        else:
            dist = base_dist + speed * 0.07
            extra = math.radians(self.chase_yaw)
            back = Vec3(math.sin(yr + extra), math.cos(yr + extra), 0)
            desired = Vec3(
                x - back.getX() * dist,
                y - back.getY() * dist,
                z + height + self.chase_pitch + min(2.5, speed * 0.03),
            )
        k = min(1.0, 4.4 * dt)
        self._cam_pos = self._cam_pos + (desired - self._cam_pos) * k
        self.camera.setPos(self._cam_pos)
        look = Vec3(x, y, z) + forward * (5.0 + speed * 0.06)
        look.setZ(z + 0.6)
        self.camera.lookAt(look)
        self.sky.setPos(self._cam_pos)

    def sample_cerber_bgr(self) -> np.ndarray:
        if hasattr(self, "last_display_rgb") and self.last_display_rgb is not None:
            return self.last_display_rgb[:, :, ::-1].copy()
        return np.zeros((self.win_h, self.win_w, 3), dtype=np.uint8)

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
        lo = max(2.2, self.preview_dist * 0.35)
        hi = min(22.0, max(8.0, self.preview_dist * 2.4))
        self.preview_dist = float(np.clip(self.preview_dist * (0.9 if delta > 0 else 1.1), lo, hi))

    def reset_preview(self) -> None:
        self.auto_orbit = True
        self.preview_heading = 28.0
        self.preview_pitch = 12.0
        self._fit_hangar_camera()

    @property
    def vehicle(self):
        return self.dynamics.vehicle_state()

    def _collect_runtime(self) -> None:
        st = self.world.stats()
        self.runtime.sectors_loaded = int(st["sectors"])
        self.runtime.props_active = int(st["props"])
        self.runtime.activity_lod = self.activity.lod_counts()
        self.runtime.duplicate_activity = self.activity.duplicate_count()
        self.runtime.discovered = list(self.discovered_now)
        v = self.vehicle
        self.runtime.last_phase = v.flight_phase
        if v.flight_phase == "CRASHED":
            self.runtime.crashed = True
        if any(not math.isfinite(x) for x in (*v.position, v.airspeed, v.vertical_speed)):
            self.runtime.spiral = True
        if abs(v.z) > 12000.0 or v.airspeed > 220.0:
            self.runtime.spiral = True
        if self.runtime.frames % 45 == 0:
            self.runtime.sample_memory(sectors=self.runtime.sectors_loaded)

    def record_sample(self) -> dict:
        v = self.vehicle
        cam = self.camera.getPos()
        return {
            "t": v.timestamp,
            "x": v.x,
            "y": v.y,
            "z": v.z,
            "yaw": v.heading,
            "pitch": v.pitch,
            "roll": v.roll,
            "speed": v.airspeed,
            "groundspeed": v.groundspeed,
            "throttle": v.throttle,
            "phase": v.flight_phase,
            "camera": self.camera_mode,
            "cam": [float(cam.getX()), float(cam.getY()), float(cam.getZ())],
            "weather": self.world.atmosphere.preset,
            "tod": self.world.atmosphere.time_of_day_h,
            "agl": v.altitude_agl,
            "vs": v.vertical_speed,
            "frame": "blackbox_enu_v1",
        }

    def start_replay(self, folder) -> None:
        from pathlib import Path

        from .sim.world_contract import mismatch_reasons

        meta, poses, events = load_replay(Path(folder))
        reasons = mismatch_reasons(meta, self.blackbox_contract or meta)
        self.replay_warning = "; ".join(reasons)
        self.replay_poses = poses
        self.replay_events = events
        self.replay_i = 0
        self.replay_active = bool(poses)
        self.paused = False
        self.input_enabled = False
        if poses:
            self._apply_replay_pose(poses[0])

    def stop_replay(self) -> None:
        self.replay_active = False
        self.input_enabled = True

    def _apply_replay_pose(self, sample: dict) -> None:
        s = self.dynamics.state
        s.x = float(sample.get("x", s.x))
        s.y = float(sample.get("y", s.y))
        s.z = float(sample.get("z", s.z))
        s.yaw_deg = float(sample.get("yaw", s.yaw_deg))
        s.pitch_deg = float(sample.get("pitch", s.pitch_deg))
        s.roll_deg = float(sample.get("roll", s.roll_deg))
        s.speed = float(sample.get("speed", s.speed))
        s.throttle = float(sample.get("throttle", s.throttle))
        pose = (s.x, s.y, s.z, s.yaw_deg, s.pitch_deg, s.roll_deg)
        self._pose_prev = pose
        self._pose_curr = pose
        self._sync_ego(1.0)

    def _step_replay(self, dt: float) -> None:
        if not self.replay_poses:
            self.replay_active = False
            return
        self.replay_i = min(len(self.replay_poses) - 1, self.replay_i + max(1, int(dt * 20)))
        self._apply_replay_pose(self.replay_poses[self.replay_i])
        s = self.dynamics.state
        self.world.update(s.x, s.y, s.z)
        self.activity.update(dt, (s.x, s.y), self.world.ground_z)
        self._apply_flight_camera(dt)
        if self.replay_i >= len(self.replay_poses) - 1:
            self.replay_active = False

    def rebuild_hangar_line(self, definitions: list | None = None) -> None:
        for node in self.hangar_parked:
            try:
                node.removeNode()
            except Exception:
                pass
        self.hangar_parked = []
        self.hangar_line_active = False
        if not self.target.isEmpty():
            self.target.hide()
        if not self.ego.isEmpty():
            self.ego.wrtReparentTo(self.hangar_anchor)
            self.ego.setPos(0, 0, 0)
            self.ego.setHpr(0, 0, 0)
            self.ego.show()
        self._fit_hangar_camera()

    def _attach_nav_lights(self) -> None:
        prev = getattr(self, "_nav_root", None)
        if prev is not None:
            try:
                prev.removeNode()
            except Exception:
                pass
        self._nav_root = self.ego.attachNewNode("nav_lights")
        self._nav_root.setLightOff(1)
        port = self._nav_root.attachNewNode(box((0.95, 0.12, 0.10)))
        port.setPos(-0.85, 0.05, 0.06)
        port.setScale(0.08, 0.08, 0.05)
        stbd = self._nav_root.attachNewNode(box((0.10, 0.92, 0.16)))
        stbd.setPos(0.85, 0.05, 0.06)
        stbd.setScale(0.08, 0.08, 0.05)
        tail = self._nav_root.attachNewNode(box((0.95, 0.95, 0.95)))
        tail.setPos(0.0, -0.55, 0.08)
        tail.setScale(0.06, 0.06, 0.05)
        self._nav_root.hide()

    def _sync_nav_lights(self) -> None:
        if not hasattr(self, "_nav_root"):
            return
        if self.world.atmosphere.lights_on:
            self._nav_root.show()
        else:
            self._nav_root.hide()

    def _emit_flight_events(self) -> None:
        s = self.dynamics.state
        phase = s.phase.value if hasattr(s.phase, "value") else str(s.phase)
        t = float(s.flight_time)
        if phase != self._prev_phase:
            if phase == "LAUNCH":
                self.blackbox.event("LAUNCH", t=t)
            elif phase in ("TOUCHDOWN", "STOPPED"):
                self.blackbox.event("LANDING", {"grade": s.landing_grade, "vz": float(s.vz)}, t=t)
            elif phase == "CRASHED":
                self.blackbox.event("CRASH", {"vz": float(s.vz)}, t=t)
            self._prev_phase = phase
        if s.stalling and not self._prev_stall:
            self.blackbox.event("STALL", t=t)
        self._prev_stall = bool(s.stalling)
        if s.overspeed and not self._prev_overspeed:
            self.blackbox.event("OVERSPEED", t=t)
        self._prev_overspeed = bool(s.overspeed)
        lights = self.world.atmosphere.lights_on
        if lights != self._prev_lights:
            self.blackbox.event(
                "WEATHER",
                {"lights": lights, "clock": self.world.atmosphere.clock_h, "preset": self.world.atmosphere.preset},
                t=t,
            )
            self._prev_lights = lights

    def _scan_landmarks(self) -> None:
        s = self.dynamics.state
        found: list[str] = []
        for lm in self.world.graph.landmarks:
            if not lm.extra.get("discover"):
                continue
            title = str(lm.extra.get("title") or lm.kind.upper())
            if math.hypot(lm.x - s.x, lm.y - s.y) <= 800.0:
                found.append(title)
        self.discovered_now = found

    def nearby_landmarks(self, radius: float = 800.0) -> list[str]:
        s = self.dynamics.state
        out = []
        for lm in self.world.graph.landmarks:
            if not lm.extra.get("discover"):
                continue
            title = str(lm.extra.get("title") or lm.kind.upper())
            if math.hypot(lm.x - s.x, lm.y - s.y) <= radius:
                out.append(title)
        return out

    def cycle_hud_layer(self) -> str:
        order = ("clean", "flight", "operator", "engineering")
        cur = (self.hud_layer or "flight").lower()
        nxt = order[(order.index(cur) + 1) % len(order)] if cur in order else "flight"
        self.hud_layer = nxt
        self.settings.hud.layer = nxt
        self.settings.hud.preset = nxt
        self.operator_tab = nxt == "operator"
        self.settings.hud.operator_tab = self.operator_tab
        return nxt

    def set_hud_layer(self, name: str) -> None:
        self.hud_layer = name
        self.settings.hud.layer = name
        self.operator_tab = name == "operator"
        self.settings.hud.operator_tab = self.operator_tab

    def seek_replay(self, index: int) -> None:
        if not self.replay_poses:
            return
        self.replay_i = max(0, min(len(self.replay_poses) - 1, int(index)))
        self._apply_replay_pose(self.replay_poses[self.replay_i])
        s = self.dynamics.state
        self.world.update(s.x, s.y, s.z)

    def screenshot(self) -> str:
        folder = blackbox_root() / "stills"
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / time.strftime("still_%Y%m%d_%H%M%S.png")
        return self.screenshot_to(path)

    def screenshot_to(self, path) -> str:
        from pathlib import Path

        dest = Path(path)
        dest.parent.mkdir(parents=True, exist_ok=True)
        tex = self.win.getScreenshot()
        if tex:
            from panda3d.core import Filename

            tex.write(Filename.fromOsSpecific(str(dest)))
        return str(dest)

    def toggle_perf(self) -> bool:
        self.debug_perf = not self.debug_perf
        self.profiler.enabled = self.debug_perf
        return self.debug_perf

    def toggle_world_debug(self) -> bool:
        on = self.world_debug.toggle()
        self.debug_world = on
        if on:
            self.world_debug.rebuild(self.world)
        return on

    def enter_cinematic(self) -> None:
        self.cinematic = True
        self.paused = True
        self._fov_restore = float(self._fov)
        self.camera_mode = "free"

    def exit_cinematic(self) -> None:
        self.cinematic = False
        self.world.atmosphere.set_visual_clock(None)
        self.camLens.setFov(self._fov_restore)
        self._fov = self._fov_restore
        self._apply_sky(rebuild=True)

    def close_engine(self) -> None:
        self.blackbox.close()
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
        self.perf_overlay = QLabel(self)
        self.perf_overlay.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.perf_overlay.setStyleSheet(
            "QLabel { color:#D8D8D8; background:rgba(8,8,10,170); font-family:Consolas,'Courier New'; "
            "font-size:12px; padding:10px 12px; }"
        )
        self.perf_overlay.hide()
        self.perf_overlay.setAttribute(Qt.WA_TransparentForMouseEvents, True)
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
        self._key_actions = bindings_map(self._bindings)
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
        self._key_actions = bindings_map(self._bindings)

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
        if self.engine.debug_perf:
            self.perf_overlay.setText(self.engine.profiler.overlay(self.engine.runtime_scope))
            self.perf_overlay.adjustSize()
            self.perf_overlay.move(16, 16)
            self.perf_overlay.show()
            self.perf_overlay.raise_()
        else:
            self.perf_overlay.hide()
        self._frame_i += 1
        if (
            self._frame_cb is not None
            and self.engine.scene_mode == "flight"
            and self.engine.runtime_scope == "flight"
            and not self.engine.paused
            and self._frame_i % self._frame_every == 0
        ):
            if self.engine._cerber_busy:
                pass
            else:
                t0 = time.perf_counter()
                self.engine._cerber_busy = True
                try:
                    self._frame_cb(self.engine.sample_cerber_bgr())
                finally:
                    self.engine._cerber_busy = False
                    self.engine.profiler.add_ms("cerber", (time.perf_counter() - t0) * 1000.0)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if self._apply_key(event, True):
            event.accept()
            return
        event.ignore()

    def keyReleaseEvent(self, event: QKeyEvent) -> None:
        if self._apply_key(event, False):
            event.accept()
            return
        event.ignore()

    def _apply_key(self, event: QKeyEvent, pressed: bool) -> bool:
        if event.key() == Qt.Key_C:
            if pressed and not event.isAutoRepeat():
                self.engine.cycle_camera()
            return True
        action = self._key_actions.get(event.key())
        if action is None:
            return False
        if action == "launch":
            if pressed and not event.isAutoRepeat():
                self.engine.launch()
            return True
        if action == "reset":
            if pressed and not event.isAutoRepeat():
                self.engine.reset_ego()
            return True
        if action in ("pause", "mode_manual", "mode_assist", "mode_follow", "mode_mission"):
            return False
        if pressed:
            self.engine.actions.add(action)
        else:
            self.engine.actions.discard(action)
        return True

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
                if self.engine.camera_mode != "nose":
                    self.engine.training.mark_camera()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        self.engine._drag = False
        super().mouseReleaseEvent(event)

    def wheelEvent(self, event: QWheelEvent) -> None:
        if self.engine.scene_mode == "hangar":
            self.engine.hangar_zoom(event.angleDelta().y())
        event.accept()
