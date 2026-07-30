"""Soft-bus nav EKF node.

Requires real IMU + GNSS on the bus. Does not invent samples or gravity hacks.
IMU accel must already be linear acceleration ENU (driver removes g).
"""

from __future__ import annotations

import time

import numpy as np

from soft_bus.bus import SoftBus
from soft_bus.messages import (
    TOPIC_GNSS,
    TOPIC_IMU,
    TOPIC_NAV,
    GnssFix,
    ImuMsg,
    NavStateMsg,
)


class NavSoftNode:
    def __init__(self, bus: SoftBus, dt: float = 0.02) -> None:
        from perception.fusion.ekf_nav import NavEKF

        self.bus = bus
        self.ekf = NavEKF(dt=dt)
        bus.subscribe(TOPIC_IMU, self._on_imu)
        bus.subscribe(TOPIC_GNSS, self._on_gnss)

    def _on_imu(self, msg: ImuMsg) -> None:
        accel = np.asarray(msg.accel_mps2, dtype=float).reshape(3)
        self.ekf.predict_imu(accel)
        self._publish(msg.stamp_s if msg.stamp_s else time.time())

    def _on_gnss(self, msg: GnssFix) -> None:
        if not msg.fix_ok:
            return
        self.ekf.update_gnss(np.array([msg.x, msg.y, msg.z], dtype=float))
        self._publish(msg.stamp_s if msg.stamp_s else time.time())

    def _publish(self, stamp: float) -> None:
        x = self.ekf.state
        self.bus.publish(
            TOPIC_NAV,
            NavStateMsg(
                float(x[0]),
                float(x[1]),
                float(x[2]),
                float(x[3]),
                float(x[4]),
                float(x[5]),
                float("nan"),  # yaw: attitude estimator not wired — do not invent 0
                stamp,
            ),
        )


def main(bus: SoftBus | None = None) -> SoftBus:
    bus = bus or SoftBus()
    NavSoftNode(bus)
    return bus


if __name__ == "__main__":
    main()
    print("nav soft node ready")
