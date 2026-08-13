"""VehicleState / ControlInput — UI and recorder never know the FDM backend."""

from __future__ import annotations

import math
from dataclasses import dataclass

from .frames import enu_forward_mps


@dataclass(frozen=True)
class ControlInput:
    pitch: float = 0.0
    roll: float = 0.0
    yaw: float = 0.0
    throttle: float = 0.0
    mode: str = "MANUAL"


@dataclass(frozen=True)
class VehicleState:
    position: tuple[float, float, float]
    orientation: tuple[float, float, float]
    linear_velocity: tuple[float, float, float]
    angular_velocity: tuple[float, float, float]
    airspeed: float
    groundspeed: float
    altitude_agl: float
    altitude_msl: float
    roll: float
    pitch: float
    heading: float
    vertical_speed: float
    throttle: float
    on_ground: bool
    flight_phase: str
    timestamp: float

    @property
    def x(self) -> float:
        return self.position[0]

    @property
    def y(self) -> float:
        return self.position[1]

    @property
    def z(self) -> float:
        return self.position[2]


def from_arcade(state) -> VehicleState:
    heading = float(state.yaw_deg)
    speed = float(state.speed)
    ve, vn = enu_forward_mps(speed, heading)
    vz = float(state.vz)
    gs = math.hypot(ve, vn)
    phase = state.phase.value if hasattr(state.phase, "value") else str(state.phase)
    on_gnd = phase in ("GROUND", "READY", "STOPPED", "GROUND_ROLL", "LANDED", "CRASHED")
    return VehicleState(
        position=(float(state.x), float(state.y), float(state.z)),
        orientation=(float(state.roll_deg), float(state.pitch_deg), heading),
        linear_velocity=(ve, vn, vz),
        angular_velocity=(
            math.radians(float(state.roll_rate)),
            math.radians(float(state.pitch_rate)),
            math.radians(float(state.yaw_rate)),
        ),
        airspeed=speed,
        groundspeed=gs,
        altitude_agl=float(state.agl),
        altitude_msl=float(state.z),
        roll=float(state.roll_deg),
        pitch=float(state.pitch_deg),
        heading=heading,
        vertical_speed=vz,
        throttle=float(state.throttle),
        on_ground=on_gnd,
        flight_phase=phase,
        timestamp=float(state.flight_time),
    )
