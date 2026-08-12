"""GSC mission soft node — plan sequence → DMI offers."""

from __future__ import annotations

import time
from pathlib import Path

from dmi.coordinator import GroundSwarmCoordinator
from dmi.messages import (
    TOPIC_DMI_AGENT_STATUS,
    TOPIC_DMI_INTENT,
    TOPIC_DMI_TASK_CLAIM,
    TOPIC_DMI_TASK_OFFER,
    AgentStatus,
    TaskClaim,
)
from planning.missions.executor import MissionExecutor
from planning.missions.plan import load_mission_plan
from soft_bus.bus import SoftBus


def _default_plan() -> Path:
    return Path(__file__).resolve().parents[2] / "planning" / "missions" / "plans" / "inspect_powerline_v1.yaml"


class MissionSoftNode:
    def __init__(self, bus: SoftBus, *, plan_path: Path | None = None) -> None:
        self.bus = bus
        self.coord = GroundSwarmCoordinator()
        self.exec = MissionExecutor(self.coord, load_mission_plan(plan_path or _default_plan()))
        bus.subscribe(TOPIC_DMI_AGENT_STATUS, self._on_status)
        bus.subscribe(TOPIC_DMI_TASK_CLAIM, self._on_claim)

    def _on_status(self, st: AgentStatus) -> None:
        self.coord.upsert_agent(st)
        self._try_alloc()

    def _on_claim(self, claim: TaskClaim) -> None:
        self.exec.on_claim(claim, now_s=time.time())
        self._try_alloc()

    def _try_alloc(self) -> None:
        offer = self.exec.tick(now_s=time.time())
        if offer is None:
            return
        self.bus.publish(TOPIC_DMI_TASK_OFFER, offer)
        self.bus.publish(TOPIC_DMI_INTENT, offer.intent)


def main(bus: SoftBus | None = None) -> SoftBus:
    bus = bus or SoftBus()
    MissionSoftNode(bus)
    return bus


if __name__ == "__main__":
    main()
    print("mission soft node ready")
