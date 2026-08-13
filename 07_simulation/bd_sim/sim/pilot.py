"""DemoPilot — MANUAL / ASSIST / FOLLOW / MISSION. Not ArduPlane. Not L0."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import yaml

from .dynamics import VehicleState, _wrap180
from .entities import TargetScript, los_to_target
from .events import EventKind, SimEvent


@dataclass
class Stick:
    pitch: float = 0.0
    roll: float = 0.0
    yaw: float = 0.0
    throttle: float = 0.0
    launch: bool = False


@dataclass
class MissionState:
    name: str = ""
    idx: int = 0
    waypoints: list[dict] = field(default_factory=list)
    loiter_t: float = 0.0
    done: bool = False
    timeout_s: float = 180.0
    bounds_m: float = 400.0
    t0: float = 0.0


class DemoPilot:
    MODES = ("MANUAL", "ASSIST", "FOLLOW", "MISSION")

    def __init__(self) -> None:
        self.mode = "MANUAL"
        self.mission = MissionState()
        self._lost_t = 0.0

    def set_mode(self, mode: str) -> None:
        if mode in self.MODES:
            self.mode = mode
            if mode != "FOLLOW":
                self._lost_t = 0.0

    def load_mission(self, path: Path, t_now: float) -> None:
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        self.mission = MissionState(
            name=str(raw.get("name", path.stem)),
            waypoints=list(raw.get("waypoints", [])),
            timeout_s=float(raw.get("timeout_s", 180)),
            bounds_m=float(raw.get("bounds_m", 400)),
            t0=t_now,
        )
        self.mode = "MISSION"

    def step(
        self,
        dt: float,
        stick: Stick,
        ego: VehicleState,
        target: TargetScript,
        t_now: float,
        has_track: bool,
    ) -> tuple[Stick, list[SimEvent]]:
        events: list[SimEvent] = []
        out = Stick(
            pitch=stick.pitch,
            roll=stick.roll,
            yaw=stick.yaw,
            throttle=stick.throttle,
            launch=stick.launch,
        )
        if self.mode == "MANUAL":
            return out, events

        dist, bearing, dz = los_to_target(ego, target)
        yaw_err = _wrap180(bearing - ego.yaw_deg)

        if self.mode in ("ASSIST", "FOLLOW"):
            if not has_track:
                self._lost_t += dt
                if self._lost_t > 1.5 and self.mode == "FOLLOW":
                    self.mode = "ASSIST"
                    events.append(SimEvent(EventKind.FOLLOW_ABORT, t_now, "lost track"))
                    events.append(SimEvent(EventKind.LOST_TARGET, t_now, "FOLLOW→ASSIST"))
            else:
                self._lost_t = 0.0

        if self.mode == "ASSIST":
            gain = 0.45 if has_track else 0.0
            assist = float(np.clip(yaw_err / 40.0, -1.0, 1.0)) * gain
            out.roll = float(np.clip(out.roll + assist, -1.0, 1.0))
            return out, events

        if self.mode == "FOLLOW":
            # lead-pursuit, load-factor limited, deadzone — not velocity snap
            if abs(yaw_err) < 6.0:
                aim = 0.0
            else:
                aim = float(np.clip(yaw_err / 35.0, -1.0, 1.0))
            out.roll = float(np.clip(aim * 0.7, -0.75, 0.75))
            # distance hold ~45 m via pitch/throttle, not homing
            dist_err = dist - 45.0
            out.pitch = float(np.clip(-0.015 * dz - 0.008 * dist_err, -0.45, 0.45))
            if dist > 70.0:
                out.throttle = 0.35
            elif dist < 28.0:
                out.throttle = -0.25
            else:
                out.throttle = 0.05
            out.yaw = 0.0
            return out, events

        # MISSION
        ev = self._mission(dt, ego, t_now, out)
        events.extend(ev)
        return out, events

    def _mission(
        self,
        dt: float,
        ego: VehicleState,
        t_now: float,
        out: Stick,
    ) -> list[SimEvent]:
        events: list[SimEvent] = []
        m = self.mission
        if m.done:
            out.pitch = out.roll = 0.0
            out.throttle = 0.0
            return events
        if t_now - m.t0 > m.timeout_s:
            m.done = True
            events.append(SimEvent(EventKind.MISSION_TIMEOUT, t_now, m.name))
            return events
        if abs(ego.x) > m.bounds_m or abs(ego.y) > m.bounds_m:
            events.append(SimEvent(EventKind.OUT_OF_BOUNDS, t_now, f"{ego.x:.0f},{ego.y:.0f}"))
            m.idx = 0
        if m.idx >= len(m.waypoints):
            m.done = True
            return events
        wp = m.waypoints[m.idx]
        kind = str(wp.get("kind", "goto_xyz"))
        tx, ty, tz = float(wp["x"]), float(wp["y"]), float(wp["z"])
        radius = float(wp.get("radius_m", 20.0))
        if not ego.launched:
            out.launch = True
            out.throttle = 1.0
            return events
        dx, dy, dz = tx - ego.x, ty - ego.y, tz - ego.z
        dist_h = float(np.hypot(dx, dy))
        bearing = float(np.degrees(np.arctan2(dx, dy)))
        yaw_err = _wrap180(bearing - ego.yaw_deg)
        out.roll = float(np.clip(yaw_err / 40.0, -0.7, 0.7))
        out.pitch = float(np.clip(dz * 0.02, -0.4, 0.4))
        out.throttle = 0.15 if dist_h > radius else -0.05

        if kind == "loiter":
            # circle around wp
            ang = np.arctan2(ego.x - tx, ego.y - ty)
            tgt_ang = ang + 0.35
            cx = tx + radius * np.sin(tgt_ang)
            cy = ty + radius * np.cos(tgt_ang)
            b = float(np.degrees(np.arctan2(cx - ego.x, cy - ego.y)))
            out.roll = float(np.clip(_wrap180(b - ego.yaw_deg) / 40.0, -0.65, 0.65))
            out.pitch = float(np.clip((tz - ego.z) * 0.02, -0.35, 0.35))
            out.throttle = 0.05
            m.loiter_t += dt
            if m.loiter_t >= float(wp.get("duration_s", 10.0)):
                m.loiter_t = 0.0
                m.idx += 1
                events.append(SimEvent(EventKind.WAYPOINT, t_now, f"loiter done {m.idx}"))
            return events

        if dist_h < radius and abs(dz) < 12.0:
            m.idx += 1
            m.loiter_t = 0.0
            events.append(SimEvent(EventKind.WAYPOINT, t_now, f"{kind} {m.idx}"))
        return events
