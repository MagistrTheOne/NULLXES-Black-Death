"""SoftBus trajectory node — intent + nav → current GoalMsg."""

from __future__ import annotations

import time

from dmi.messages import TOPIC_DMI_INTENT, SwarmIntent
from planning.trajectory.planner import TrajectoryPlanner
from soft_bus.bus import SoftBus
from soft_bus.messages import TOPIC_GOAL, TOPIC_NAV, GoalMsg, NavStateMsg


class TrajSoftNode:
    def __init__(self, bus: SoftBus) -> None:
        self.bus = bus
        self.planner = TrajectoryPlanner()
        self._nav: NavStateMsg | None = None
        bus.subscribe(TOPIC_DMI_INTENT, self._on_intent)
        bus.subscribe(TOPIC_NAV, self._on_nav)

    def _on_intent(self, intent: SwarmIntent) -> None:
        self.planner.set_intent(intent)
        self._publish(intent.trace_id)

    def _on_nav(self, nav: NavStateMsg) -> None:
        self._nav = nav
        self._publish("")

    def _publish(self, trace_id: str) -> None:
        if self._nav is None:
            return
        goal = self.planner.tick(self._nav, stamp_s=time.time(), trace_id=trace_id)
        if goal is None:
            return
        self.bus.publish(TOPIC_GOAL, goal)


def main(bus: SoftBus | None = None) -> SoftBus:
    bus = bus or SoftBus()
    TrajSoftNode(bus)
    return bus


if __name__ == "__main__":
    main()
    print("traj soft node ready")
