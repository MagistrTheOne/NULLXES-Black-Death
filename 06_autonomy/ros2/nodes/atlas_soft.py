"""GSC ATLAS node — CopSnapshot from DMI status → AllocationPlan. No cameras."""

from __future__ import annotations

import time

from atlas.dmi_adapter import apply_plan
from atlas.messages import (
    TOPIC_ATLAS_HEALTH,
    TOPIC_ATLAS_PLAN,
    CopAgent,
    CopSector,
    CopSnapshot,
)
from atlas.planner import AtlasPlanner
from dmi.coordinator import GroundSwarmCoordinator
from dmi.messages import (
    TOPIC_DMI_AGENT_STATUS,
    TOPIC_DMI_INTENT,
    TOPIC_DMI_TASK_CLAIM,
    TOPIC_DMI_TASK_OFFER,
    AgentStatus,
    Sector,
    TaskClaim,
)
from soft_bus.bus import SoftBus


class AtlasSoftNode:
    def __init__(self, bus: SoftBus) -> None:
        self.bus = bus
        self.planner = AtlasPlanner()
        self.coord = GroundSwarmCoordinator()
        self._agents: dict[str, AgentStatus] = {}
        self._sectors: dict[str, Sector] = {}
        bus.subscribe(TOPIC_DMI_AGENT_STATUS, self._on_status)
        bus.subscribe(TOPIC_DMI_TASK_CLAIM, self._on_claim)

    def register_sector(self, sector: Sector) -> None:
        self._sectors[sector.sector_id] = sector
        self.coord.upsert_sector(sector)

    def _on_status(self, st: AgentStatus) -> None:
        self._agents[st.agent_id] = st
        self.coord.upsert_agent(st)
        self._tick()

    def _on_claim(self, claim: TaskClaim) -> None:
        self.coord.on_claim(claim)

    def _tick(self) -> None:
        now = time.time()
        snap = CopSnapshot(
            agents=[
                CopAgent(a.agent_id, a.x, a.y, a.z, a.soc, a.payload_frac, a.health_factor)
                for a in self._agents.values()
            ],
            sectors=[
                CopSector(s.sector_id, s.x, s.y, s.z, s.assigned_agent)
                for s in self._sectors.values()
            ],
            stamp_s=now,
        )
        plan = self.planner.plan(snap)
        self.bus.publish(TOPIC_ATLAS_PLAN, plan)
        self.bus.publish(
            TOPIC_ATLAS_HEALTH,
            {
                "model_id": plan.model,
                "onnx": self.planner.using_onnx,
                "stamp_s": now,
            },
        )
        for offer in apply_plan(self.coord, plan, now_s=now):
            self.bus.publish(TOPIC_DMI_TASK_OFFER, offer)
            self.bus.publish(TOPIC_DMI_INTENT, offer.intent)


def main(bus: SoftBus | None = None) -> SoftBus:
    bus = bus or SoftBus()
    AtlasSoftNode(bus)
    return bus


if __name__ == "__main__":
    main()
    print("atlas soft node ready")
