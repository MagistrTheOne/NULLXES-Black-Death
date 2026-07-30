"""Alpha behaviour tree modes — pure Python source of truth."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class FlightMode(str, Enum):
    NOMINAL = "NOMINAL"
    DEGRADED_PROP = "DEGRADED_PROP"
    DEGRADED_SENS = "DEGRADED_SENS"
    DEGRADED_COMPUTE = "DEGRADED_COMPUTE"
    SAFE_LOITER = "SAFE_LOITER"
    RTB = "RTB"


@dataclass
class HealthFlags:
    thrusters_ok: int = 0
    cams_ok: int = 0
    imu_ok: int = 0
    gnss_ok: bool = False
    lidar_ok: bool = False
    compute_peer_alive: bool = False
    battery_soc: float = 0.0
    nav_integrity: bool = False


@dataclass
class AlphaBT:
    mode: FlightMode = FlightMode.SAFE_LOITER
    history: list[str] = field(default_factory=list)

    def tick(self, h: HealthFlags) -> FlightMode:
        prev = self.mode
        if h.battery_soc < 0.12 or not h.nav_integrity or h.thrusters_ok == 0:
            self.mode = FlightMode.SAFE_LOITER
        elif h.battery_soc < 0.25:
            self.mode = FlightMode.RTB
        elif not h.compute_peer_alive and self.mode != FlightMode.DEGRADED_COMPUTE:
            self.mode = FlightMode.DEGRADED_COMPUTE
        elif h.thrusters_ok < 2:
            self.mode = FlightMode.DEGRADED_PROP
        elif h.cams_ok < 2 or h.imu_ok < 1 or not h.gnss_ok or not h.lidar_ok:
            self.mode = FlightMode.DEGRADED_SENS
        else:
            self.mode = FlightMode.NOMINAL
        if self.mode != prev:
            self.history.append(f"{prev.value}->{self.mode.value}")
        return self.mode
