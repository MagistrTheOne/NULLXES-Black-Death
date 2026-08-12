"""MissionExecutor sequence + REJECT does not advance; next agent allocated."""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "06_autonomy"))

from dmi.coordinator import GroundSwarmCoordinator
from dmi.messages import AgentStatus, TaskClaim, TaskClaimKind
from planning.missions import MissionExecutor, load_mission_plan


PLAN = REPO / "06_autonomy" / "planning" / "missions" / "plans" / "inspect_powerline_v1.yaml"


def _agents(coord: GroundSwarmCoordinator) -> None:
    coord.upsert_agent(
        AgentStatus("bj-1", 0.0, 0.0, 0.0, soc=0.9, payload_frac=0.0, health_factor=1.0, stamp_s=1.0)
    )
    coord.upsert_agent(
        AgentStatus("bj-2", 200.0, 0.0, 0.0, soc=0.9, payload_frac=0.0, health_factor=1.0, stamp_s=1.0)
    )


def test_sequence_accept_advances():
    plan = load_mission_plan(PLAN)
    coord = GroundSwarmCoordinator(max_distance_m=1000.0)
    _agents(coord)
    ex = MissionExecutor(coord, plan)
    o1 = ex.tick(now_s=1.0)
    assert o1 is not None
    assert o1.intent.kind.value == "EXPLORE_SECTOR"
    assert ex.on_claim(
        TaskClaim(o1.offer_id, o1.task_id, o1.agent_id, TaskClaimKind.ACCEPT, stamp_s=1.1),
        now_s=1.1,
    )
    assert ex.index == 1
    o2 = ex.tick(now_s=1.2)
    assert o2 is not None
    assert o2.intent.kind.value == "GOTO_XYZ"
    assert ex.on_claim(
        TaskClaim(o2.offer_id, o2.task_id, o2.agent_id, TaskClaimKind.ACCEPT, stamp_s=1.3),
        now_s=1.3,
    )
    assert ex.done()


def test_reject_does_not_advance_reallocates():
    plan = load_mission_plan(PLAN)
    coord = GroundSwarmCoordinator(max_distance_m=1000.0)
    _agents(coord)
    ex = MissionExecutor(coord, plan)
    o1 = ex.tick(now_s=1.0)
    assert o1 is not None
    first = o1.agent_id
    assert ex.on_claim(
        TaskClaim(o1.offer_id, o1.task_id, o1.agent_id, TaskClaimKind.REJECT, stamp_s=1.1),
        now_s=1.1,
    )
    assert ex.index == 0
    o2 = ex.tick(now_s=1.2)
    assert o2 is not None
    assert o2.agent_id != first
    assert o2.intent.kind.value == "EXPLORE_SECTOR"
