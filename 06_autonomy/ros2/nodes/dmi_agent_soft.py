"""Soft-bus onboard DMI agent — bridges accepted intent to planning GoalMsg."""

from __future__ import annotations

import time
from pathlib import Path

from dmi.event_bus import EventFilter, fingerprint_health, fingerprint_intent
from dmi.intent_bridge import intent_to_goal_gated
from dmi.messages import (
    TOPIC_DMI_AGENT_STATUS,
    TOPIC_DMI_SWARM_HEALTH,
    TOPIC_DMI_TASK_CLAIM,
    TOPIC_DMI_TASK_OFFER,
    TOPIC_DMI_WORLD_FACT,
    AgentStatus,
    SwarmHealthMsg,
    TaskOffer,
    WorldFact,
)
from dmi.mission_policy import MissionPolicyGate, load_mission_profile
from dmi.swarm_agent import SwarmAgent
from dmi.swarm_health import health_to_factor
from soft_bus.bus import SoftBus
from soft_bus.messages import TOPIC_GOAL, TOPIC_POLICY_DECISION


def _default_profile() -> Path:
    return (
        Path(__file__).resolve().parents[2]
        / "mission_profiles"
        / "inspection.powerline.v1.yaml"
    )


class DmiAgentSoftNode:
    def __init__(
        self,
        bus: SoftBus,
        agent_id: str = "bj-1",
        *,
        profile_path: Path | None = None,
    ) -> None:
        self.bus = bus
        self.agent = SwarmAgent(agent_id=agent_id)
        self._events = EventFilter()
        self._nav_xyz = (0.0, 0.0, 0.0)
        self._soc = 1.0
        self._payload = 0.0
        self.gate = MissionPolicyGate(load_mission_profile(profile_path or _default_profile()))
        bus.subscribe(TOPIC_DMI_TASK_OFFER, self._on_offer)
        bus.subscribe(TOPIC_DMI_WORLD_FACT, self._on_fact)

    def set_local_state(
        self,
        *,
        x: float,
        y: float,
        z: float,
        soc: float,
        payload_frac: float = 0.0,
    ) -> None:
        self._nav_xyz = (x, y, z)
        self._soc = soc
        self._payload = payload_frac

    def _on_offer(self, offer: TaskOffer) -> None:
        now = time.time()
        claim = self.agent.handle_offer(offer, now_s=now, reported_ok=True)
        if claim is None:
            return
        self.bus.publish(TOPIC_DMI_TASK_CLAIM, claim)
        if claim.kind.value == "ACCEPT" and self.agent.last_intent is not None:
            intent = self.agent.last_intent
            fp = fingerprint_intent(
                intent.intent_id,
                intent.kind.value,
                intent.sector_id,
                intent.x,
                intent.y,
                intent.z,
            )
            if self._events.should_publish("intent", fp):
                goal, decision = intent_to_goal_gated(intent, self.gate, stamp_s=now)
                self.bus.publish(TOPIC_POLICY_DECISION, decision)
                if goal is not None:
                    self.bus.publish(TOPIC_GOAL, goal)
        self._publish_health(now)

    def _on_fact(self, fact: WorldFact) -> None:
        self.agent.ingest_fact(fact, now_s=time.time())

    def publish_status(self) -> None:
        now = time.time()
        self.agent.update_health(now_s=now, reported_ok=True)
        x, y, z = self._nav_xyz
        self.bus.publish(
            TOPIC_DMI_AGENT_STATUS,
            AgentStatus(
                agent_id=self.agent.agent_id,
                x=x,
                y=y,
                z=z,
                soc=self._soc,
                payload_frac=self._payload,
                health_factor=health_to_factor(self.agent.health),
                stamp_s=now,
            ),
        )
        self._publish_health(now)

    def _publish_health(self, now: float) -> None:
        st = self.agent.health.value
        fp = fingerprint_health(self.agent.agent_id, st)
        if not self._events.should_publish("health", fp):
            return
        self.bus.publish(
            TOPIC_DMI_SWARM_HEALTH,
            SwarmHealthMsg(self.agent.agent_id, st, now),
        )


def main(bus: SoftBus | None = None, agent_id: str = "bj-1") -> SoftBus:
    bus = bus or SoftBus()
    DmiAgentSoftNode(bus, agent_id=agent_id)
    return bus


if __name__ == "__main__":
    main()
    print("dmi agent soft node ready")
