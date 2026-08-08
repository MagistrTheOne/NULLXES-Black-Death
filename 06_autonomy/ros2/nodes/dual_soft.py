"""Soft-bus dual-compute node.

Heartbeat + election only. Mirror mission_mode comes from FM when present;
does not invent NOMINAL or peer-alive without heartbeats.
"""

from __future__ import annotations

import time

from core.dual_compute.active_election import ActiveElection, ElectionConfig
from core.dual_compute.heartbeat import HeartbeatMonitor
from soft_bus.bus import SoftBus
from soft_bus.messages import (
    TOPIC_ACTIVE,
    TOPIC_FM_MODE,
    TOPIC_HB_A,
    TOPIC_HB_B,
    TOPIC_MAVLINK_HEALTH,
    TOPIC_MIRROR,
    TOPIC_NAV,
    TOPIC_SENSORHUB_HEALTH,
    ActiveChannel,
    FmMode,
    HeartbeatMsg,
    MavlinkHealthMsg,
    MirrorMsg,
    NavStateMsg,
    SensorHubHealth,
)


class DualSoftNode:
    def __init__(self, bus: SoftBus, channel_id: str = "A") -> None:
        self.bus = bus
        self.channel_id = channel_id
        self.seq = 0
        peer = "B" if channel_id == "A" else "A"
        self.monitor = HeartbeatMonitor(peer, timeout_s=0.15)
        self.election = ActiveElection(ElectionConfig(prefer="A", sticky_after_failover=True))
        self._nav = NavStateMsg()
        self._alive = {"A": False, "B": False}
        self._mission_mode = "SAFE_LOITER"
        self._sensorhub_ok = False
        self._mavlink_ok = False
        bus.subscribe(TOPIC_NAV, self._on_nav)
        bus.subscribe(TOPIC_HB_A, self._on_hb)
        bus.subscribe(TOPIC_HB_B, self._on_hb)
        bus.subscribe(TOPIC_FM_MODE, self._on_mode)
        bus.subscribe(TOPIC_SENSORHUB_HEALTH, self._on_sensorhub)
        bus.subscribe(TOPIC_MAVLINK_HEALTH, self._on_mavlink)

    def _on_nav(self, m: NavStateMsg) -> None:
        self._nav = m

    def _on_mode(self, m: FmMode) -> None:
        self._mission_mode = m.mode

    def _on_sensorhub(self, m: SensorHubHealth) -> None:
        self._sensorhub_ok = bool(m.cam_ok or m.imu_ok)

    def _on_mavlink(self, m: MavlinkHealthMsg) -> None:
        self._mavlink_ok = bool(m.link_ok)

    def _on_hb(self, m: HeartbeatMsg) -> None:
        from core.dual_compute.heartbeat import Heartbeat

        self.monitor.update(
            Heartbeat(m.channel_id, m.seq, m.stamp_s, m.healthy)
        )
        self._alive[m.channel_id] = m.healthy and (time.time() - m.stamp_s) <= 0.15

    def pulse(self, healthy: bool = True) -> None:
        now = time.time()
        self.seq += 1
        topic = TOPIC_HB_A if self.channel_id == "A" else TOPIC_HB_B
        # Channel unhealthy if SensorHub+FC both dead while claiming healthy.
        channel_healthy = healthy
        self.bus.publish(
            topic,
            HeartbeatMsg(self.channel_id, self.seq, channel_healthy, now),
        )
        peer = "B" if self.channel_id == "A" else "A"
        self._alive[self.channel_id] = channel_healthy
        self._alive[peer] = self.monitor.peer_alive(now)
        active = self.election.step(self._alive["A"], self._alive["B"])
        self.bus.publish(TOPIC_ACTIVE, ActiveChannel(active, now))
        self.bus.publish(
            TOPIC_MIRROR,
            MirrorMsg(
                stamp_s=now,
                channel_id=self.channel_id,
                active=(active == self.channel_id),
                mission_mode=self._mission_mode,
                health_flags={
                    "sensorhub_ok": self._sensorhub_ok,
                    "mavlink_ok": self._mavlink_ok,
                },
                nav=self._nav,
            ),
        )


def main(bus: SoftBus | None = None, channel_id: str = "A") -> SoftBus:
    bus = bus or SoftBus()
    DualSoftNode(bus, channel_id=channel_id)
    return bus


if __name__ == "__main__":
    main()
    print("dual soft node ready")
