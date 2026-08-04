"""Arcade fixed-wing dynamics — viz only."""

from __future__ import annotations

from dataclasses import dataclass

from ursina import Vec3, time


@dataclass
class ArcadeState:
    speed: float = 14.0
    throttle: float = 0.55


class ArcadeFlyer:
    def __init__(self, entity, preset) -> None:
        self.e = entity
        self.preset = preset
        self.st = ArcadeState()

    def reset(self, pos: Vec3, rot: Vec3 | None = None) -> None:
        self.e.position = pos
        self.e.rotation = rot or Vec3(0, 0, 0)
        self.st = ArcadeState()

    def update(
        self,
        *,
        pitch: float,
        roll: float,
        yaw: float,
        throttle_delta: float,
        assist_yaw: float = 0.0,
    ) -> None:
        dt = time.dt
        p = self.preset
        self.st.throttle = max(0.05, min(1.0, self.st.throttle + throttle_delta * dt))
        target_spd = 6.0 + self.st.throttle * (p.max_speed - 6.0)
        self.st.speed += (target_spd - self.st.speed) * min(1.0, 2.5 * dt)

        rate = p.turn_rate * dt
        self.e.rotate(Vec3(pitch * rate, (yaw + assist_yaw) * rate, -roll * rate))

        # mild auto-level roll when idle
        if abs(roll) < 0.05:
            self.e.rotation_z *= max(0.0, 1.0 - 1.8 * dt)

        forward = self.e.forward
        self.e.position += forward * self.st.speed * dt
        # soft floor
        if self.e.y < 2.0:
            self.e.y = 2.0
            self.e.rotation_x = min(self.e.rotation_x, 5)
