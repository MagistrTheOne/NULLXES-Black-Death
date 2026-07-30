"""Map isolation + faults → behaviour / guidance limits."""

from __future__ import annotations

from dataclasses import dataclass

from planning.behaviour.alpha_bt import FlightMode, HealthFlags
from .detection import DetectedFaults
from .isolation import IsolationMask


@dataclass
class ReconfigOut:
    mode_hint: FlightMode
    max_thrust: float
    allow_mission: bool


def reconfigure(faults: DetectedFaults, mask: IsolationMask) -> tuple[HealthFlags, ReconfigOut]:
    thrusters_ok = sum(1 for x in mask.motors_enabled if x)
    cams_ok = sum(1 for x in mask.cams_enabled if x)
    imu_ok = sum(1 for x in mask.imus_enabled if x)
    # battery_soc left 0 here — caller must set from real SOC telemetry
    h = HealthFlags(
        thrusters_ok=thrusters_ok,
        cams_ok=cams_ok,
        imu_ok=imu_ok,
        gnss_ok=mask.use_gnss and not faults.gnss_stale,
        lidar_ok=mask.lidar_enabled,
        compute_peer_alive=not faults.peer_dead,
        battery_soc=0.0,
        nav_integrity=imu_ok >= 1 and (mask.use_gnss or cams_ok >= 1),
    )
    if faults.battery_critical or thrusters_ok == 0 or not h.nav_integrity:
        out = ReconfigOut(FlightMode.SAFE_LOITER, 0.2, False)
    elif faults.battery_low:
        out = ReconfigOut(FlightMode.RTB, 0.45, False)
    elif thrusters_ok < 2:
        out = ReconfigOut(FlightMode.DEGRADED_PROP, 0.55, False)
    elif faults.peer_dead:
        out = ReconfigOut(FlightMode.DEGRADED_COMPUTE, 0.7, True)
    elif cams_ok < 2 or imu_ok < 1 or not mask.lidar_enabled or faults.gnss_stale:
        out = ReconfigOut(FlightMode.DEGRADED_SENS, 0.6, True)
    else:
        out = ReconfigOut(FlightMode.NOMINAL, 1.0, True)
    return h, out
