"""Soft-bus Ground Swarm Coordinator node (host-side DMI)."""

from __future__ import annotations

import time

from dmi.coordinator import GroundSwarmCoordinator
from dmi.event_bus import EventFilter, fingerprint_task
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


class DmiCoordinatorSoftNode:
    def __init__(self, bus: SoftBus) -> None:
        self.bus = bus
        self.coord = GroundSwarmCoordinator()
        self._events = EventFilter()
        bus.subscribe(TOPIC_DMI_AGENT_STATUS, self._on_status)
        bus.subscribe(TOPIC_DMI_TASK_CLAIM, self._on_claim)

    def _on_status(self, st: AgentStatus) -> None:
        self.coord.upsert_agent(st)

    def _on_claim(self, claim: TaskClaim) -> None:
        self.coord.on_claim(claim)

    def register_sector(self, sector: Sector) -> None:
        self.coord.upsert_sector(sector)

    def allocate_sector(self, sector_id: str) -> None:
        offer = self.coord.allocate_explore_sector(sector_id)
        if offer is None:
            return
        fp = fingerprint_task(offer.offer_id, "OFFER")
        if not self._events.should_publish("offer", fp):
            return
        self.bus.publish(TOPIC_DMI_TASK_OFFER, offer)
        self.bus.publish(TOPIC_DMI_INTENT, offer.intent)


def main(bus: SoftBus | None = None) -> SoftBus:
    bus = bus or SoftBus()
    DmiCoordinatorSoftNode(bus)
    return bus


if __name__ == "__main__":
    main()
    print("dmi coordinator soft node ready")
