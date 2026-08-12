"""ATLAS SoftBus messages — AllocationPlan / CopSnapshot. Never GuidanceIntent."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Assignment:
    agent_id: str
    sector_id: str
    intent_kind: str
    score: float
    reason_code: str = "SCORE"


@dataclass(frozen=True)
class AllocationPlan:
    plan_id: str
    stamp_s: float
    trace_id: str = ""
    model: str = "BLACK-ATLAS-ALLOC-01"
    assignments: tuple[Assignment, ...] = ()
    releases: tuple[tuple[str, str, str], ...] = ()
    holds: tuple[str, ...] = ()


@dataclass(frozen=True)
class CopAgent:
    agent_id: str
    x: float
    y: float
    z: float
    soc: float
    payload_frac: float
    health_factor: float


@dataclass(frozen=True)
class CopSector:
    sector_id: str
    x: float
    y: float
    z: float
    assigned_agent: str = ""


@dataclass
class CopSnapshot:
    agents: list[CopAgent] = field(default_factory=list)
    sectors: list[CopSector] = field(default_factory=list)
    stamp_s: float = 0.0
    trace_id: str = ""


TOPIC_ATLAS_PLAN = "/bd/atlas/plan"
TOPIC_ATLAS_COP = "/bd/atlas/cop"
TOPIC_ATLAS_HEALTH = "/bd/atlas/health"
