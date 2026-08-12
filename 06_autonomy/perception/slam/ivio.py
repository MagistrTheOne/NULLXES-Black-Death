"""IVioProvider SoftBus contract — honest names; native OpenVINS/Basalt unlinked."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Protocol

from soft_bus.messages import ImuMsg, ImageMsg, VioStateMsg

_ACCEL_EPS = 0.15


class IVioProvider(Protocol):
    name: str

    def reset(self) -> None: ...

    def push_imu(self, imu: ImuMsg) -> None: ...

    def push_image(self, image: ImageMsg) -> VioStateMsg | None: ...

    def latest(self) -> VioStateMsg | None: ...


def _uninit(provider: str, image: ImageMsg) -> VioStateMsg:
    return VioStateMsg(
        status="uninit",
        provider=provider,
        stamp_s=image.stamp_s,
        stamp_ns=image.stamp_ns,
        sensor_stamp_ns=image.sensor_stamp_ns,
        cov_xx=1.0e6,
        cov_yy=1.0e6,
        cov_zz=1.0e6,
    )


class NullVioProvider:
    """Always uninit — no pose claimed."""

    name = "null"

    def reset(self) -> None:
        return None

    def push_imu(self, imu: ImuMsg) -> None:
        return None

    def push_image(self, image: ImageMsg) -> VioStateMsg | None:
        return _uninit(self.name, image)

    def latest(self) -> VioStateMsg | None:
        return None


class OpenVinsProvider(NullVioProvider):
    """Deploy slot. Native OpenVINS is GPL-3 and not linked — stay uninit."""

    name = "openvins"


class BasaltProvider(NullVioProvider):
    """Deploy slot. Native Basalt not linked — stay uninit."""

    name = "basalt"


@dataclass
class _VoState:
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    vx: float = 0.0
    vy: float = 0.0
    vz: float = 0.0


class NullxesVoProvider:
    """NULLXES-VO v0: Lucas–Kanade flow + IMU integrate only if accel is non-zero."""

    name = "nullxes_vo"

    def __init__(self, *, flow_scale: float = 0.01) -> None:
        self._pose = _VoState()
        self._last_imu_ns = 0
        self._prev_gray = None
        self._latest: VioStateMsg | None = None
        self._flow_ok = False
        self._flow_scale = flow_scale
        self._last_accel = (0.0, 0.0, 0.0)

    def reset(self) -> None:
        self._pose = _VoState()
        self._latest = None
        self._prev_gray = None
        self._flow_ok = False
        self._last_imu_ns = 0

    def push_imu(self, imu: ImuMsg) -> None:
        self._last_accel = tuple(float(a) for a in imu.accel_mps2)
        ns = imu.sensor_stamp_ns or imu.stamp_ns or int(imu.stamp_s * 1e9)
        ax, ay, az = self._last_accel
        mag = (ax * ax + ay * ay + az * az) ** 0.5
        if mag <= _ACCEL_EPS:
            self._last_imu_ns = ns
            return
        if self._last_imu_ns > 0 and ns > self._last_imu_ns:
            dt = (ns - self._last_imu_ns) * 1e-9
            self._pose.vx += ax * dt
            self._pose.vy += ay * dt
            self._pose.vz += az * dt
            self._pose.x += self._pose.vx * dt
            self._pose.y += self._pose.vy * dt
            self._pose.z += self._pose.vz * dt
        self._last_imu_ns = ns

    def push_image(self, image: ImageMsg) -> VioStateMsg | None:
        import numpy as np

        bgr = getattr(image, "bgr", None)
        if bgr is None:
            self._flow_ok = False
            msg = _uninit(self.name, image)
            self._latest = msg
            return msg
        try:
            import cv2

            gray = cv2.cvtColor(np.asarray(bgr), cv2.COLOR_BGR2GRAY)
        except Exception:
            self._flow_ok = False
            msg = _uninit(self.name, image)
            self._latest = msg
            return msg

        had_prev = self._prev_gray is not None
        if had_prev and self._prev_gray.shape == gray.shape:
            h, w = gray.shape
            ys, xs = np.mgrid[8 : h - 8 : 16, 8 : w - 8 : 16]
            pts = np.stack([xs.ravel(), ys.ravel()], axis=1).astype(np.float32)
            if pts.shape[0] >= 8:
                nxt, st, _err = cv2.calcOpticalFlowPyrLK(self._prev_gray, gray, pts, None)
                if nxt is not None and st is not None:
                    good = st.reshape(-1) == 1
                    if int(good.sum()) >= 8:
                        d = nxt[good] - pts[good]
                        self._pose.vx = float(d[:, 0].mean()) * self._flow_scale
                        self._pose.vy = float(d[:, 1].mean()) * self._flow_scale
                        self._pose.x += self._pose.vx
                        self._pose.y += self._pose.vy
                        self._flow_ok = True
                    else:
                        self._flow_ok = False
                else:
                    self._flow_ok = False
            else:
                self._flow_ok = False
        else:
            self._flow_ok = False
        self._prev_gray = gray

        status = "ok" if self._flow_ok else ("degraded" if had_prev else "uninit")
        cov = 0.25 if status == "ok" else 25.0 if status == "degraded" else 1.0e6
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
