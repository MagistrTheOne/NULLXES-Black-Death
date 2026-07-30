"""Isolate failed channels (logical masks)."""

from __future__ import annotations

from dataclasses import dataclass, field

from .detection import DetectedFaults


@dataclass
class IsolationMask:
    motors_enabled: list[bool] = field(default_factory=lambda: [True, True])
    cams_enabled: list[bool] = field(default_factory=lambda: [True, True, True, True])
    imus_enabled: list[bool] = field(default_factory=lambda: [True, True])
    lidar_enabled: bool = True
    use_gnss: bool = True


def isolate(faults: DetectedFaults, mask: IsolationMask | None = None) -> IsolationMask:
    m = mask or IsolationMask()
    for i in faults.thruster_fail:
        if 0 <= i < len(m.motors_enabled):
            m.motors_enabled[i] = False
    for i in faults.cam_fail:
        if 0 <= i < len(m.cams_enabled):
            m.cams_enabled[i] = False
    for i in faults.imu_fail:
        if 0 <= i < len(m.imus_enabled):
            m.imus_enabled[i] = False
    if faults.lidar_fail:
        m.lidar_enabled = False
    if faults.gnss_stale:
        m.use_gnss = False
    return m
