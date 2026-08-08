"""IVioProvider SoftBus contract — OpenVINS / Basalt behind one interface."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Protocol

from soft_bus.messages import ImuMsg, ImageMsg, VioStateMsg


class IVioProvider(Protocol):
    name: str

    def reset(self) -> None: ...

    def push_imu(self, imu: ImuMsg) -> None: ...

    def push_image(self, image: ImageMsg) -> VioStateMsg | None: ...

    def latest(self) -> VioStateMsg | None: ...


@dataclass
class _Pose:
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    vx: float = 0.0
    vy: float = 0.0
    vz: float = 0.0


class NullVioProvider:
    """Always uninit — safe default until native lib linked."""

    name = "null"

    def reset(self) -> None:
        return None

    def push_imu(self, imu: ImuMsg) -> None:
        return None

    def push_image(self, image: ImageMsg) -> VioStateMsg | None:
        return VioStateMsg(
            status="uninit",
            provider=self.name,
            stamp_s=image.stamp_s,
            stamp_ns=image.stamp_ns,
            sensor_stamp_ns=image.sensor_stamp_ns,
        )

    def latest(self) -> VioStateMsg | None:
        return None


class OpenVinsProvider:
    """
    SoftBus-facing OpenVINS wrapper.

    Native OpenVINS process is linked at deploy time. Until then this provider
    integrates IMU for a dead-reckoning placeholder and marks status=degraded
    (never claims ok without native backend).
    """

    name = "openvins"

    def __init__(self) -> None:
        self._pose = _Pose()
        self._last_imu_ns = 0
        self._native = False
        self._latest: VioStateMsg | None = None

    def reset(self) -> None:
        self._pose = _Pose()
        self._latest = None

    def push_imu(self, imu: ImuMsg) -> None:
        ns = imu.sensor_stamp_ns or imu.stamp_ns or int(imu.stamp_s * 1e9)
        if self._last_imu_ns > 0 and ns > self._last_imu_ns:
            dt = (ns - self._last_imu_ns) * 1e-9
            ax, ay, az = imu.accel_mps2
            self._pose.vx += ax * dt
            self._pose.vy += ay * dt
            self._pose.vz += az * dt
            self._pose.x += self._pose.vx * dt
            self._pose.y += self._pose.vy * dt
            self._pose.z += self._pose.vz * dt
        self._last_imu_ns = ns

    def push_image(self, image: ImageMsg) -> VioStateMsg | None:
        status = "ok" if self._native else "degraded"
        cov = 0.05 if self._native else 25.0
        msg = VioStateMsg(
            x=self._pose.x,
            y=self._pose.y,
            z=self._pose.z,
            vx=self._pose.vx,
            vy=self._pose.vy,
            vz=self._pose.vz,
            cov_xx=cov,
            cov_yy=cov,
            cov_zz=cov,
            status=status,
            provider=self.name,
            stamp_s=image.stamp_s or time.time(),
            stamp_ns=image.stamp_ns,
            sensor_stamp_ns=image.sensor_stamp_ns,
            frame_id="body",
        )
        self._latest = msg
        return msg

    def latest(self) -> VioStateMsg | None:
        return self._latest


class BasaltProvider(OpenVinsProvider):
    """Same SoftBus contract; native Basalt linked at deploy (BSD-3)."""

    name = "basalt"
