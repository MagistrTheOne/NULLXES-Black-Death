"""Arcade fixed-wing dynamics v1 — complete Studio flight model (Panda3D Z-up)."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class WingParams:
    key: str
    title: str
    scale: float
    max_speed: float
    turn_rate_deg: float
    color_rgb: tuple[float, float, float]
    accent_rgb: tuple[float, float, float]


def preset(key: str) -> WingParams:
    return PRESETS.get(key, PRESETS["ar_wing"])


PRESETS: dict[str, WingParams] = {
    "s800": WingParams(
        key="s800",
        title="Reptile S800-class",
        scale=1.0,
        max_speed=28.0,
        turn_rate_deg=95.0,
        color_rgb=(0.14, 0.15, 0.16),
        accent_rgb=(0.86, 0.35, 0.16),
    ),
    "ar_wing": WingParams(
        key="ar_wing",
        title="AR Wing Pro-class",
        scale=1.35,
        max_speed=34.0,
        turn_rate_deg=75.0,
        color_rgb=(0.05, 0.05, 0.055),
        accent_rgb=(0.70, 0.12, 0.16),
    ),
}


@dataclass
class PoseState:
    x: float = 0.0
    y: float = 0.0
    z: float = 14.0
    pitch_deg: float = 0.0
    yaw_deg: float = 0.0
    roll_deg: float = 0.0
    speed: float = 14.0
    throttle: float = 0.55


class ArcadeDynamics:
    """Thrust + drag-lite + gravity + attitude rates (arcade, complete v1)."""

    def __init__(self, params: WingParams) -> None:
        self.params = params
        self.state = PoseState()

    def reset(self) -> None:
        self.state = PoseState()

    def set_params(self, params: WingParams) -> None:
        self.params = params

    def step(
        self,
        dt: float,
        *,
        pitch_cmd: float,
        roll_cmd: float,
        yaw_cmd: float,
        throttle_cmd: float,
        assist_yaw: float = 0.0,
        wind_xy: tuple[float, float] = (0.0, 0.0),
        sim_speed: float = 1.0,
        ground_collision: bool = True,
        difficulty: str = "standard",
        fail_throttle: bool = False,
    ) -> PoseState:
        dt = float(max(1e-4, min(0.05, dt))) * float(max(0.25, min(2.0, sim_speed)))
        p = self.params
        s = self.state
        diff = (difficulty or "standard").lower()
        turn_mul = {"arcade": 1.25, "strict": 0.72}.get(diff, 1.0)
        sink_mul = {"arcade": 0.7, "strict": 1.35}.get(diff, 1.0)

        s.throttle = float(np.clip(s.throttle + throttle_cmd * dt * 0.7, 0.05, 1.0))
        if fail_throttle:
            s.throttle = float(max(0.05, s.throttle * (1.0 - 0.35 * dt)))
        target_spd = 6.0 + s.throttle * (p.max_speed - 6.0)
        s.speed += (target_spd - s.speed) * min(1.0, 2.4 * dt)

        rate = p.turn_rate_deg * turn_mul * dt
        s.pitch_deg = float(np.clip(s.pitch_deg + pitch_cmd * rate, -55.0, 55.0))
        s.roll_deg = float(np.clip(s.roll_deg + roll_cmd * rate, -70.0, 70.0))
        yaw_input = yaw_cmd + assist_yaw
        s.yaw_deg = (s.yaw_deg + yaw_input * rate + s.roll_deg * 0.35 * dt) % 360.0

        if abs(roll_cmd) < 0.05:
            s.roll_deg *= max(0.0, 1.0 - 1.6 * dt)

        pr = np.radians(s.pitch_deg)
        yr = np.radians(s.yaw_deg)
        # Panda3D: +X right, +Y forward, +Z up
        forward = np.array(
            [
                np.sin(yr) * np.cos(pr),
                np.cos(yr) * np.cos(pr),
                np.sin(pr),
            ],
            dtype=np.float64,
        )
        lift_factor = 0.85 + 0.35 * s.throttle
        sink = -9.81 * (1.0 - min(1.0, lift_factor * (s.speed / p.max_speed))) * sink_mul
        vel = forward * s.speed
        s.x += float(vel[0] * dt + wind_xy[0] * dt)
        s.y += float(vel[1] * dt + wind_xy[1] * dt)
        s.z += float(vel[2] * dt + sink * dt * 0.35)

        if ground_collision:
            if s.z < 2.0:
                s.z = 2.0
                s.pitch_deg = max(s.pitch_deg, -8.0)
                s.speed *= 0.92
        elif s.z < 0.15:
            s.z = 0.15
            s.speed *= 0.4
            s.pitch_deg = 0.0

        return s

    def position(self) -> tuple[float, float, float]:
        s = self.state
        return s.x, s.y, s.z

    def hpr(self) -> tuple[float, float, float]:
        s = self.state
        return s.yaw_deg, s.pitch_deg, s.roll_deg
