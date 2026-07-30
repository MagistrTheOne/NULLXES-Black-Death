"""Onboard L6 SwarmAgent — ACCEPT/REJECT offers; retain last intent if center lost."""

from __future__ import annotations

import time
from dataclasses import dataclass, field

from .messages import (
    SwarmIntent,
    TaskClaim,
    TaskClaimKind,
    TaskOffer,
    WorldFact,
)
from .swarm_health import SwarmHealthState, age_health
from .world_cache import SharedWorldCache


@dataclass
class SwarmAgent:
    agent_id: str
    accept_min_score: float = 0.0
    coordinator_timeout_s: float = 3.0
    world: SharedWorldCache = field(default_factory=SharedWorldCache)
    last_intent: SwarmIntent | None = None
    health: SwarmHealthState = SwarmHealthState.LOST
    _last_offer_from_coord_s: float | None = None
    _last_status_stamp_s: float | None = None

    def note_coordinator_traffic(self, stamp_s: float) -> None:
        self._last_offer_from_coord_s = stamp_s

    def coordinator_link_ok(self, *, now_s: float) -> bool:
        if self._last_offer_from_coord_s is None:
            return False
        return (now_s - self._last_offer_from_coord_s) <= self.coordinator_timeout_s

    def update_health(
        self,
        *,
        now_s: float,
        reported_ok: bool,
        status_stamp_s: float | None = None,
    ) -> SwarmHealthState:
        stamp = status_stamp_s if status_stamp_s is not None else now_s
        self._last_status_stamp_s = stamp
        self.health = age_health(
            previous=self.health,
            now_s=now_s,
            last_status_stamp_s=self._last_status_stamp_s,
            reported_ok=reported_ok,
        )
        return self.health

    def handle_offer(
        self,
        offer: TaskOffer,
        *,
        now_s: float | None = None,
        reported_ok: bool = True,
    ) -> TaskClaim | None:
        """Accept exclusive offer for this agent_id; else None (ignore)."""
        now = now_s if now_s is not None else time.time()
        if offer.agent_id != self.agent_id:
            return None
        self.note_coordinator_traffic(offer.stamp_s or now)
        self.update_health(now_s=now, reported_ok=reported_ok)

        if self.health == SwarmHealthState.LOST or not reported_ok:
            return TaskClaim(
                offer_id=offer.offer_id,
                task_id=offer.task_id,
                agent_id=self.agent_id,
                kind=TaskClaimKind.REJECT,
                stamp_s=now,
            )
        if offer.score < self.accept_min_score:
            return TaskClaim(
                offer_id=offer.offer_id,
                task_id=offer.task_id,
                agent_id=self.agent_id,
                kind=TaskClaimKind.REJECT,
                stamp_s=now,
            )
        self.last_intent = offer.intent
        return TaskClaim(
            offer_id=offer.offer_id,
            task_id=offer.task_id,
            agent_id=self.agent_id,
            kind=TaskClaimKind.ACCEPT,
            stamp_s=now,
        )

    def ingest_fact(self, fact: WorldFact, *, now_s: float | None = None) -> bool:
        now = now_s if now_s is not None else time.time()
        return self.world.upsert(fact, now_s=now)
    #возвращает последний intent, который был назначен этому агенту
    def active_intent(self, *, now_s: float | None = None) -> SwarmIntent | None:
        """Current mission intent — kept when coordinator link is lost."""
        return self.last_intent
