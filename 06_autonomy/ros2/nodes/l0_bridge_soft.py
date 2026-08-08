"""L0Bridge SoftBus node — Goal/Setpoint → ArduPlane Guided commands."""

from __future__ import annotations

import time

from l0_bridge.arduplane_adapter import ArduPlaneAdapter, HomeOrigin, PlaneGuidedCommand
from soft_bus.bus import SoftBus
from soft_bus.messages import (
    TOPIC_GOAL,
    TOPIC_MAVLINK_HEALTH,
    TOPIC_PLANE_CMD,
    TOPIC_SETPOINT,
    GoalMsg,
    Setpoint,
)


class L0BridgeSoftNode:
    def __init__(
        self,
        bus: SoftBus,
        *,
        home: HomeOrigin | None = None,
        stream_attitude: bool = False,
    ) -> None:
        self.bus = bus
        self.adapter = ArduPlaneAdapter(home=home, prefer_attitude_stream=stream_attitude)
        self.stream_attitude = stream_attitude
        self._last_cmd: PlaneGuidedCommand | None = None
        bus.subscribe(TOPIC_GOAL, self._on_goal)
        if stream_attitude:
            bus.subscribe(TOPIC_SETPOINT, self._on_setpoint)

    def on_heartbeat(self, *, mode: str, armed: bool) -> None:
        h = self.adapter.on_heartbeat(mode=mode, armed=armed)
        self.bus.publish(TOPIC_MAVLINK_HEALTH, h)

    def mark_link_lost(self) -> None:
        cmd = self.adapter.mark_link_lost()
        self._publish_cmd(cmd)
        self.bus.publish(TOPIC_MAVLINK_HEALTH, self.adapter.health)

    def _on_goal(self, goal: GoalMsg) -> None:
        cmd = self.adapter.goal_to_command(goal)
        self._publish_cmd(cmd)

    def _on_setpoint(self, sp: Setpoint) -> None:
        cmd = self.adapter.setpoint_to_attitude(sp)
        self._publish_cmd(cmd)

    def _publish_cmd(self, cmd: PlaneGuidedCommand) -> None:
        self._last_cmd = cmd
        payload = self.adapter.to_mavlink_dict(cmd)
        payload["stamp_s"] = cmd.stamp_s or time.time()
        self.bus.publish(TOPIC_PLANE_CMD, payload)

    @property
    def last_cmd(self) -> PlaneGuidedCommand | None:
        return self._last_cmd


def main(bus: SoftBus | None = None) -> SoftBus:
    bus = bus or SoftBus()
    L0BridgeSoftNode(bus)
    return bus


if __name__ == "__main__":
    main()
