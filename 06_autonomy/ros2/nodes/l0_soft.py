"""L0 soft node — Python control law (same gains as C++ InnerLoop).

Requires real IMU samples and setpoints on the bus from avionics/drivers.
Does not invent sensor data.
"""

from __future__ import annotations

import time

from control.inner_loop_py import ImuPy, InnerLoopPy, SetpointPy
from soft_bus.bus import SoftBus
from soft_bus.messages import (
    TOPIC_ACTUATORS,
    TOPIC_IMU,
    TOPIC_L0_HEALTH,
    TOPIC_SETPOINT,
    Actuators,
    ImuMsg,
    L0Health,
    Setpoint,
)


class L0SoftNode:
    def __init__(self, bus: SoftBus) -> None:
        self.bus = bus
        self.loop = InnerLoopPy()
        self._imu: ImuMsg | None = None
        self._last_sp_t = 0.0
        bus.subscribe(TOPIC_SETPOINT, self._on_sp)
        bus.subscribe(TOPIC_IMU, self._on_imu)

    def _on_imu(self, m: ImuMsg) -> None:
        self._imu = m

    def _on_sp(self, sp: Setpoint) -> None:
        now = time.time()
        self._last_sp_t = now
        if self._imu is None:
            self.bus.publish(
                TOPIC_L0_HEALTH,
                L0Health(esc_ok=False, imu_ok=False, bus_ok=True, stamp_s=now),
            )
            return
        if not sp.valid or (sp.stamp_s and now - sp.stamp_s > 0.2):
            self.loop.set_hold_attitude()
        cmd = self.loop.step(
            SetpointPy(sp.roll_rad, sp.pitch_rad, sp.yaw_rate_rps, sp.thrust_norm, sp.valid),
            ImuPy(self._imu.gyro_rps, self._imu.accel_mps2),
            InnerLoopPy.DT,
        )
        self.bus.publish(
            TOPIC_ACTUATORS,
            Actuators(cmd.elevon_left, cmd.elevon_right, cmd.motor_main, now),
        )
        # esc_ok stays False until ESC/current telemetry exists
        self.bus.publish(
            TOPIC_L0_HEALTH,
            L0Health(esc_ok=False, imu_ok=True, bus_ok=True, stamp_s=now),
        )
    def tick_hold_watchdog(self) -> None:
        now = time.time()
        if self._imu is None:
            return
        if self._last_sp_t and now - self._last_sp_t > 0.2:
            self.loop.set_hold_attitude()
            cmd = self.loop.step(
                SetpointPy(valid=False),
                ImuPy(self._imu.gyro_rps, self._imu.accel_mps2),
                InnerLoopPy.DT,
            )
            self.bus.publish(
                TOPIC_ACTUATORS,
                Actuators(cmd.elevon_left, cmd.elevon_right, cmd.motor_main, now),
            )


def main(bus: SoftBus | None = None) -> SoftBus:
    bus = bus or SoftBus()
    L0SoftNode(bus)
    return bus


if __name__ == "__main__":
    main()
