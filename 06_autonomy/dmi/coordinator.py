"""Ground Swarm Coordinator — Mission Score allocation; exclusive TaskOffer."""

from __future__ import annotations

import math
import time
import uuid
from dataclasses import dataclass, field

from .messages import (
    AgentStatus,
    IntentKind,
    Sector,
    SwarmIntent,
    TaskClaim,
    TaskClaimKind,
    TaskOffer,
)
from .mission_score import AgentScoreInput, MissionScoreWeights, select_best_agent


@dataclass
class GroundSwarmCoordinator:
    max_distance_m: float = 500.0
    weights: MissionScoreWeights = field(default_factory=MissionScoreWeights)
    offer_timeout_s: float = 2.0
    _agents: dict[str, AgentStatus] = field(default_factory=dict)
    _sectors: dict[str, Sector] = field(default_factory=dict)
    _open_offer: TaskOffer | None = None
    _open_offer_deadline: float = 0.0
    _assigned_tasks: dict[str, str] = field(default_factory=dict)  # task_id -> agent_id

    def upsert_agent(self, status: AgentStatus) -> None:
        self._agents[status.agent_id] = status

    def upsert_sector(self, sector: Sector) -> None:
        self._sectors[sector.sector_id] = sector

    def on_claim(self, claim: TaskClaim, *, now_s: float | None = None) -> bool:
        """Apply ACCEPT/REJECT. Returns True if offer closed successfully."""
        now = now_s if now_s is not None else time.time()
        if self._open_offer is None:
            return False
        if claim.offer_id != self._open_offer.offer_id:
            return False
        if claim.agent_id != self._open_offer.agent_id:
            return False
        if now > self._open_offer_deadline:
            self._open_offer = None
            return False
        if claim.kind == TaskClaimKind.ACCEPT:
            self._assigned_tasks[claim.task_id] = claim.agent_id
            if self._open_offer.intent.sector_id:
                sec = self._sectors.get(self._open_offer.intent.sector_id)
                if sec is not None:
                    self._sectors[sec.sector_id] = Sector(
                        sec.sector_id, sec.x, sec.y, sec.z, claim.agent_id
                    )
            self._open_offer = None
            return True
        # REJECT — clear offer so allocator may retry another agent later
        self._open_offer = None
        return True

    def expire_offer(self, *, now_s: float | None = None) -> None:
        now = now_s if now_s is not None else time.time()
        if self._open_offer is not None and now > self._open_offer_deadline:
            self._open_offer = None

    def allocate_explore_sector(
        self,
        sector_id: str,
        *,
        now_s: float | None = None,
    ) -> TaskOffer | None:
        """Exclusive offer to best agent for exploring a known sector."""
        now = now_s if now_s is not None else time.time()
        self.expire_offer(now_s=now)
        if self._open_offer is not None:
            return None
        sector = self._sectors.get(sector_id)
        if sector is None:
            raise ValueError(f"unknown sector {sector_id!r}")
        candidates: list[AgentScoreInput] = []
        for st in self._agents.values():
            dist = math.hypot(st.x - sector.x, st.y - sector.y)
            candidates.append(
                AgentScoreInput(
                    agent_id=st.agent_id,
                    distance_m=dist,
                    soc=st.soc,
                    payload_frac=st.payload_frac,
                    health_factor=st.health_factor,
                )
            )
        best = select_best_agent(
            candidates, max_distance_m=self.max_distance_m, weights=self.weights
        )
        if best is None:
            return None
        agent_id, score = best
        task_id = f"explore-{sector_id}"
        if self._assigned_tasks.get(task_id) == agent_id:
            return None
        intent = SwarmIntent(
            intent_id=str(uuid.uuid4()),
            kind=IntentKind.EXPLORE_SECTOR,
            agent_id=agent_id,
            sector_id=sector_id,
            x=sector.x,
            y=sector.y,
            z=sector.z,
            stamp_s=now,
        )
        offer = TaskOffer(
            offer_id=str(uuid.uuid4()),
            task_id=task_id,
            agent_id=agent_id,
            intent=intent,
            score=score,
            stamp_s=now,
        )
        self._open_offer = offer
        self._open_offer_deadline = now + self.offer_timeout_s
        return offer
