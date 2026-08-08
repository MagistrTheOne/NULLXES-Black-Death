"""DMI SoftBus / ROS logical messages and topic names."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class TaskClaimKind(str, Enum):
    ACCEPT = "ACCEPT"
    REJECT = "REJECT"


class IntentKind(str, Enum):
    EXPLORE_SECTOR = "EXPLORE_SECTOR"
    GOTO_XYZ = "GOTO_XYZ"
    LOITER = "LOITER"


class RelationKind(str, Enum):
    INSIDE = "INSIDE"
    NEAR = "NEAR"
    MOVING_TOWARD = "MOVING_TOWARD"
    MOVING_AWAY = "MOVING_AWAY"
    OBSERVED_BY = "OBSERVED_BY"
    ASSIGNED_TO = "ASSIGNED_TO"
    LOST_BY = "LOST_BY"
    HANDOFF_TO = "HANDOFF_TO"


class OntologyEventKind(str, Enum):
    DETECTED = "DETECTED"
    UPDATED = "UPDATED"
    LOST = "LOST"
    ENTER_SECTOR = "ENTER_SECTOR"
    ALERT = "ALERT"
    HANDOFF = "HANDOFF"
    LINK_LOST = "LINK_LOST"
    POLICY_DENY = "POLICY_DENY"


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
    trace_id: str = ""


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
    """Observation snapshot — projection of a WorldObject at a stamp."""

    fact_id: str
    kind: str
    x: float
    y: float
    z: float
    confidence: float
    source_id: str
    stamp_s: float = 0.0
    frame_id: str = "enu"
    cov_xx: float = 1.0e6
    cov_yy: float = 1.0e6
    cov_zz: float = 1.0e6
    stamp_ns: int = 0
    sensor_stamp_ns: int = 0
    trace_id: str = ""
    track_id: int = -1


@dataclass(frozen=True)
class WorldObject:
    """Persistent entity in DMI World Ontology (DMI_ONTOLOGY.md)."""

    object_id: str
    type: str
    x: float
    y: float
    z: float
    confidence: float
    source_id: str
    track_id: int = -1
    vx: float = 0.0
    vy: float = 0.0
    vz: float = 0.0
    cov_xx: float = 1.0e6
    cov_yy: float = 1.0e6
    cov_zz: float = 1.0e6
    frame_id: str = "enu"
    state: str = "observed"  # observed|tentative|confirmed|lost|handoff
    attrs: dict[str, str] = field(default_factory=dict)
    first_seen_s: float = 0.0
    last_seen_s: float = 0.0
    stamp_ns: int = 0
    sensor_stamp_ns: int = 0
    trace_id: str = ""


@dataclass(frozen=True)
class Relation:
    relation_id: str
    kind: str
    subject_id: str
    object_id: str
    confidence: float = 1.0
    stamp_s: float = 0.0
    trace_id: str = ""


@dataclass(frozen=True)
class OntologyEvent:
    event_id: str
    kind: str
    object_id: str = ""
    agent_id: str = ""
    detail: str = ""
    stamp_s: float = 0.0
    trace_id: str = ""


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
TOPIC_DMI_WORLD_OBJECT = "/bd/dmi/world_object"
TOPIC_DMI_RELATION = "/bd/dmi/relation"
TOPIC_DMI_EVENT = "/bd/dmi/event"
TOPIC_DMI_SWARM_HEALTH = "/bd/dmi/swarm_health"
