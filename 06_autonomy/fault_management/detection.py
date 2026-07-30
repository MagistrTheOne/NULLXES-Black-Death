"""Fault detection from health signals."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class RawHealth:
    motor_thrust_residual: tuple[float, float]  # |cmd-meas| fraction
    cams_alive: tuple[bool, bool, bool, bool]
    imu_alive: tuple[bool, bool]
    gnss_fix_age_s: float
    lidar_alive: bool
    peer_heartbeat_age_s: float
    battery_soc: float


@dataclass
class DetectedFaults:
    thruster_fail: list[int]
    cam_fail: list[int]
    imu_fail: list[int]
    gnss_stale: bool
    lidar_fail: bool
    peer_dead: bool
    battery_low: bool
    battery_critical: bool


def detect(h: RawHealth) -> DetectedFaults:
    thr = [i for i, r in enumerate(h.motor_thrust_residual) if r > 0.55]
    cams = [i for i, ok in enumerate(h.cams_alive) if not ok]
    imus = [i for i, ok in enumerate(h.imu_alive) if not ok]
    return DetectedFaults(
        thruster_fail=thr,
        cam_fail=cams,
        imu_fail=imus,
        gnss_stale=h.gnss_fix_age_s > 5.0,
        lidar_fail=not h.lidar_alive,
        peer_dead=h.peer_heartbeat_age_s > 0.15,
        battery_low=h.battery_soc < 0.25,
        battery_critical=h.battery_soc < 0.12,
    )
