"""Soft-bus FM + behaviour tree node.

Does not invent healthy sensors. Requires real vision/L0/SOC (and GNSS age).
LiDAR is optional until a lidar health topic exists (`lidar_reported`).
"""

from __future__ import annotations

import time

from soft_bus.bus import SoftBus
from soft_bus.messages import (
    TOPIC_BATTERY_SOC,
    TOPIC_FM_MODE,
    TOPIC_GNSS,
    TOPIC_HB_A,
    TOPIC_HB_B,
    TOPIC_L0_HEALTH,
    TOPIC_VISION_HEALTH,
    FmMode,
    GnssFix,
    HeartbeatMsg,
    L0Health,
    VisionHealth,
)
from fault_management.detection import RawHealth, detect
from fault_management.isolation import isolate
from fault_management.reconfiguration import reconfigure
from planning.behaviour.alpha_bt import AlphaBT


class FmBtSoftNode:
    def __init__(self, bus: SoftBus, channel: str = "A") -> None:
        self.bus = bus
        self.channel = channel
        self.bt = AlphaBT()
        self._vision: VisionHealth | None = None
        self._l0: L0Health | None = None
        self._hb_a: HeartbeatMsg | None = None
        self._hb_b: HeartbeatMsg | None = None
        self._soc: float | None = None
        self._gnss_stamp: float | None = None
        self._gnss_ok = False
        # No lidar health topic yet — do not invent alive, do not treat as failed.
        self._lidar_alive = False
        self._lidar_reported = False
        bus.subscribe(TOPIC_VISION_HEALTH, self._on_vision)
        bus.subscribe(TOPIC_L0_HEALTH, self._on_l0)
        bus.subscribe(TOPIC_HB_A, lambda m: setattr(self, "_hb_a", m))
        bus.subscribe(TOPIC_HB_B, lambda m: setattr(self, "_hb_b", m))
        bus.subscribe(TOPIC_BATTERY_SOC, self._on_soc)
        bus.subscribe(TOPIC_GNSS, self._on_gnss)

    def _on_vision(self, m: VisionHealth) -> None:
        self._vision = m
        self.tick()

    def _on_l0(self, m: L0Health) -> None:
        self._l0 = m
        self.tick()

    def _on_soc(self, m: float) -> None:
        self._soc = float(m)
        self.tick()

    def _on_gnss(self, m: GnssFix) -> None:
        self._gnss_ok = bool(m.fix_ok)
        self._gnss_stamp = m.stamp_s if m.stamp_s else time.time()
        self.tick()

    def tick(self) -> None:
        if self._vision is None or self._l0 is None or self._soc is None:
            return

        now = time.time()
        peer = self._hb_b if self.channel == "A" else self._hb_a
        peer_age = 999.0 if peer is None else max(0.0, now - peer.stamp_s)
        cams = max(0, int(self._vision.cams_alive))
        cam_flags = tuple(i < cams for i in range(4))

        if self._gnss_stamp is None:
            gnss_age = 999.0
        else:
            gnss_age = max(0.0, now - self._gnss_stamp)
            if not self._gnss_ok:
                gnss_age = 999.0

        # ESC ok ≠ measured residual; without thrust telemetry do not invent residuals.
        # Map esc_ok → residual 0 (healthy) or 1.0 (failed channel).
        esc = self._l0.esc_ok
        residual = (0.0, 0.0) if esc else (1.0, 1.0)

        raw = RawHealth(
            motor_thrust_residual=residual,
            cams_alive=cam_flags,
            imu_alive=(self._l0.imu_ok, False),
            gnss_fix_age_s=gnss_age,
            lidar_alive=self._lidar_alive,
            lidar_reported=self._lidar_reported,
            peer_heartbeat_age_s=peer_age,
            battery_soc=self._soc,
        )
        faults = detect(raw)
        mask = isolate(faults)
        health, _ = reconfigure(faults, mask, lidar_reported=self._lidar_reported)
        health.battery_soc = self._soc
        health.compute_peer_alive = peer_age <= 0.15 and bool(peer and peer.healthy)
        mode = self.bt.tick(health)
        self.bus.publish(TOPIC_FM_MODE, FmMode(mode.value, now))


def main(bus: SoftBus | None = None, channel: str = "A") -> SoftBus:
    bus = bus or SoftBus()
    FmBtSoftNode(bus, channel=channel)
    return bus


if __name__ == "__main__":
    main()
    print("fm_bt soft node ready")
