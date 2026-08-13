"""Ego / target / background kinematic extras. CERBER only sees ego camera."""

from __future__ import annotations

import math

from .dynamics import VehicleState


class TargetScript:
    def __init__(self) -> None:
        self.phase = 0.0
        self.x = 20.0
        self.y = 50.0
        self.z = 22.0
        self.yaw_deg = 0.0

    def reset(self) -> None:
        self.phase = 0.0
        self.step(0.0)

    def step(self, dt: float) -> None:
        self.phase += dt * 0.32
        r = 32.0
        self.x = 24.0 + r * math.cos(self.phase)
        self.y = 70.0 + r * math.sin(self.phase)
        self.z = 22.0 + 4.0 * math.sin(self.phase * 2.0)
        self.yaw_deg = -math.degrees(self.phase) + 90.0

    def position(self) -> tuple[float, float, float]:
        return self.x, self.y, self.z


class BackgroundFlock:
    """Low-fidelity extras — clothoid-ish circles. No stall. No CERBER."""

    def __init__(self, n: int = 8) -> None:
        self.n = n
        self.phase = [i * 0.7 for i in range(n)]

    def poses(self, t: float) -> list[tuple[float, float, float, float]]:
        out = []
        for i, ph0 in enumerate(self.phase):
            ph = ph0 + t * (0.18 + 0.03 * i)
            r = 80.0 + 12.0 * (i % 3)
            x = math.cos(ph) * r
            y = 40.0 + math.sin(ph) * r
            z = 30.0 + 5.0 * math.sin(ph * 1.4)
            yaw = -math.degrees(ph) + 90.0
            out.append((x, y, z, yaw))
        return out


def los_to_target(ego: VehicleState, tgt: TargetScript) -> tuple[float, float, float]:
    dx = tgt.x - ego.x
    dy = tgt.y - ego.y
    dz = tgt.z - ego.z
    dist = math.sqrt(dx * dx + dy * dy + dz * dz)
    bearing = math.degrees(math.atan2(dx, dy))
    return dist, bearing, dz
