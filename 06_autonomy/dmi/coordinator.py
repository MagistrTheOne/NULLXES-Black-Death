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
    _assigned_tasks: dict[str, str] = field(default_factory=dict)
    _rejected: dict[str, set[str]] = field(default_factory=dict)

    def upsert_agent(self, status: AgentStatus) -> None:
        self._agents[status.agent_id] = status

    def upsert_sector(self, sector: Sector) -> None:
        self._sectors[sector.sector_id] = sector

    def on_claim(self, claim: TaskClaim, *, now_s: float | None = None) -> bool:
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
                        sec.sector_id,
                        sec.x,
                        sec.y,
                        sec.z,
                        claim.agent_id,
                        sec.xmin,
                        sec.xmax,
                        sec.ymin,
                        sec.ymax,
                        sec.spacing_m,
                    )
            self._open_offer = None
            return True
        self._rejected.setdefault(claim.task_id, set()).add(claim.agent_id)
        self._open_offer = None
        return True

    def expire_offer(self, *, now_s: float | None = None) -> None:
        now = now_s if now_s is not None else time.time()
        if self._open_offer is not None and now > self._open_offer_deadline:
            self._open_offer = None

    def _candidates(
        self,
        x: float,
        y: float,
        *,
        exclude: set[str] | None = None,
    ) -> list[AgentScoreInput]:
        skip = exclude or set()
        out: list[AgentScoreInput] = []
        for st in self._agents.values():
            if st.agent_id in skip:
                continue
            dist = math.hypot(st.x - x, st.y - y)
            out.append(
                AgentScoreInput(
                    agent_id=st.agent_id,
                    distance_m=dist,
                    soc=st.soc,
                    payload_frac=st.payload_frac,
                    health_factor=st.health_factor,
                )
            )
        return out

    def _offer(
        self,
        *,
        task_id: str,
        intent: SwarmIntent,
        score: float,
        now: float,
    ) -> TaskOffer | None:
        if self._open_offer is not None:
            return None
        if self._assigned_tasks.get(task_id) == intent.agent_id:
            return None
        offer = TaskOffer(
            offer_id=str(uuid.uuid4()),
            task_id=task_id,
            agent_id=intent.agent_id,
            intent=intent,
            score=score,
            stamp_s=now,
        )
        self._open_offer = offer
        self._open_offer_deadline = now + self.offer_timeout_s
        return offer

    def allocate_explore_sector(
        self,
        sector_id: str,
        *,
        now_s: float | None = None,
        exclude: set[str] | None = None,
    ) -> TaskOffer | None:
        now = now_s if now_s is not None else time.time()
        self.expire_offer(now_s=now)
        if self._open_offer is not None:
            return None
        sector = self._sectors.get(sector_id)
        if sector is None:
            raise ValueError(f"unknown sector {sector_id!r}")
        skip = set(exclude or ()) | self._rejected.get(f"explore-{sector_id}", set())
        best = select_best_agent(
            self._candidates(sector.x, sector.y, exclude=skip),
            max_distance_m=self.max_distance_m,
            weights=self.weights,
        )
        if best is None:
            return None
        agent_id, score = best
        task_id = f"explore-{sector_id}"
        intent = SwarmIntent(
            intent_id=str(uuid.uuid4()),
            kind=IntentKind.EXPLORE_SECTOR,
            agent_id=agent_id,
            sector_id=sector_id,
            x=sector.x,
            y=sector.y,
            z=sector.z,
            stamp_s=now,
            xmin=sector.xmin,
            xmax=sector.xmax,
            ymin=sector.ymin,
            ymax=sector.ymax,
            spacing_m=sector.spacing_m,
        )
        return self._offer(task_id=task_id, intent=intent, score=score, now=now)

    def allocate_goto(
        self,
        x: float,
        y: float,
        z: float,
        *,
        task_id: str = "goto",
        now_s: float | None = None,
        exclude: set[str] | None = None,
    ) -> TaskOffer | None:
        now = now_s if now_s is not None else time.time()
        self.expire_offer(now_s=now)
        skip = set(exclude or ()) | self._rejected.get(task_id, set())
        best = select_best_agent(
            self._candidates(x, y, exclude=skip),
            max_distance_m=self.max_distance_m,
            weights=self.weights,
        )
        if best is None:
            return None
        agent_id, score = best
        intent = SwarmIntent(
            intent_id=str(uuid.uuid4()),
            kind=IntentKind.GOTO_XYZ,
            agent_id=agent_id,
            x=x,
            y=y,
            z=z,
            stamp_s=now,
        )
        return self._offer(task_id=task_id, intent=intent, score=score, now=now)

    def allocate_loiter(
        self,
        x: float,
        y: float,
        z: float,
        *,
        task_id: str = "loiter",
        now_s: float | None = None,
        exclude: set[str] | None = None,
    ) -> TaskOffer | None:
        now = now_s if now_s is not None else time.time()
        self.expire_offer(now_s=now)
        skip = set(exclude or ()) | self._rejected.get(task_id, set())
        best = select_best_agent(
            self._candidates(x, y, exclude=skip),
            max_distance_m=self.max_distance_m,
            weights=self.weights,
        )
        if best is None:
            return None
        agent_id, score = best
        intent = SwarmIntent(
            intent_id=str(uuid.uuid4()),
            kind=IntentKind.LOITER,
            agent_id=agent_id,
            x=x,
            y=y,
            z=z,
            stamp_s=now,
        )
        return self._offer(task_id=task_id, intent=intent, score=score, now=now)
