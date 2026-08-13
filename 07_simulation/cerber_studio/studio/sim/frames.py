"""BLACKBOX canonical frame. JSBSim never sees Panda coordinates."""

from __future__ import annotations

import math
from dataclasses import dataclass

# BLACKBOX WORLD
#   X = East
#   Y = North
#   Z = Up
# meters. Heading 0 = North, increasing clockwise toward East (aviation).
FRAME_ID = "blackbox_enu_v1"


@dataclass(frozen=True)
class EnuMeters:
    east: float
    north: float
    up: float


@dataclass(frozen=True)
class NedMeters:
    north: float
    east: float
    down: float


def enu_to_ned(east: float, north: float, up: float) -> NedMeters:
    return NedMeters(north=north, east=east, down=-up)


def ned_to_enu(north: float, east: float, down: float) -> EnuMeters:
    return EnuMeters(east=east, north=north, up=-down)


def heading_deg_from_enu_velocity(ve: float, vn: float) -> float:
    return (math.degrees(math.atan2(ve, vn)) + 360.0) % 360.0


def enu_forward_mps(speed: float, heading_deg: float) -> tuple[float, float]:
    yr = math.radians(heading_deg)
    return speed * math.sin(yr), speed * math.cos(yr)


class FrameAdapter:
    """JSBSim NED/body ↔ BLACKBOX ENU. No Panda types."""

    def to_jsbsim_ned(self, east: float, north: float, up: float) -> tuple[float, float, float]:
        ned = enu_to_ned(east, north, up)
        return ned.north, ned.east, ned.down

    def from_jsbsim_ned(self, north: float, east: float, down: float) -> tuple[float, float, float]:
        enu = ned_to_enu(north, east, down)
        return enu.east, enu.north, enu.up

    def heading_to_jsbsim_psi_deg(self, heading_deg: float) -> float:
        return heading_deg % 360.0

    def jsbsim_psi_to_heading_deg(self, psi_deg: float) -> float:
        return psi_deg % 360.0
