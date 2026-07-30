"""DMI SoftBus / ROS logical messages and topic names."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class TaskClaimKind(str, Enum):
    ACCEPT = "ACCEPT"
    REJECT = "REJECT"


class IntentKind(str, Enum):
    EXPLORE_SECTOR = "EXPLORE_SECTOR"
    GOTO_XYZ = "GOTO_XYZ"
    LOITER = "LOITER"


@dataclass(frozen=True)
class SwarmIntent:
    intent_id: str
    kind: IntentKind
    agent_id: str
    sector_id: str = ""
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    stamp_s: float = 0.0


@dataclass(frozen=True)
class TaskOffer:
    offer_id: str
    task_id: str
    agent_id: str
    intent: SwarmIntent
    score: float
    stamp_s: float = 0.0


@dataclass(frozen=True)
class TaskClaim:
    offer_id: str
    task_id: str
    agent_id: str
    kind: TaskClaimKind
    stamp_s: float = 0.0


@dataclass(frozen=True)
class AgentStatus:
    agent_id: str
    x: float
    y: float
    z: float
    soc: float
    payload_frac: float
    health_factor: float
    stamp_s: float = 0.0


@dataclass(frozen=True)
class WorldFact:
    fact_id: str
    kind: str
    x: float
    y: float
    z: float
    confidence: float
    source_id: str
    stamp_s: float = 0.0


@dataclass(frozen=True)
class SwarmHealthMsg:
    agent_id: str
    state: str
    stamp_s: float = 0.0
    detail: str = ""


@dataclass
class Sector:
    sector_id: str
    x: float
    y: float
    z: float
    assigned_agent: str = ""


TOPIC_DMI_INTENT = "/bd/dmi/intent"
TOPIC_DMI_TASK_OFFER = "/bd/dmi/task_offer"
TOPIC_DMI_TASK_CLAIM = "/bd/dmi/task_claim"
TOPIC_DMI_AGENT_STATUS = "/bd/dmi/agent_status"
TOPIC_DMI_WORLD_FACT = "/bd/dmi/world_fact"
TOPIC_DMI_SWARM_HEALTH = "/bd/dmi/swarm_health"
