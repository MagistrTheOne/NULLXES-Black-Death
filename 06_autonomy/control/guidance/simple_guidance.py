"""Guidance → L0 setpoint (pure function + buffer)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class NavState:
    x: float
    y: float
    z: float
    vx: float
    vy: float
    vz: float
    yaw: float


@dataclass
class SetpointOut:
    roll_rad: float
    pitch_rad: float
    yaw_rate_rps: float
    thrust_norm: float
    valid: bool = True


def simple_guidance(
    nav: NavState,
    target_x: float,
    target_y: float,
    target_z: float,
    cruise_thrust: float = 0.35,
) -> SetpointOut:
    import math

    dx = target_x - nav.x
    dy = target_y - nav.y
    dz = target_z - nav.z
    bearing = math.atan2(dy, dx)
    yaw_err = (bearing - nav.yaw + math.pi) % (2 * math.pi) - math.pi
    dist_xy = math.hypot(dx, dy)
    pitch = max(-0.15, min(0.15, 0.02 * dz))
    roll = max(-0.2, min(0.2, 0.4 * yaw_err))
    yaw_rate = max(-0.5, min(0.5, 1.2 * yaw_err))
    thrust = cruise_thrust if dist_xy > 5.0 else max(0.15, cruise_thrust * 0.5)
    return SetpointOut(roll, pitch, yaw_rate, thrust, True)
