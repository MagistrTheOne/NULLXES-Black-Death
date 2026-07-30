"""Coordinator exclusive allocation tests."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "06_autonomy"))

from dmi.coordinator import GroundSwarmCoordinator
from dmi.messages import AgentStatus, Sector, TaskClaim, TaskClaimKind
from dmi.swarm_agent import SwarmAgent


def test_single_owner_no_double_claim():
    coord = GroundSwarmCoordinator(max_distance_m=1000.0)
    coord.upsert_sector(Sector("B7", 100.0, 0.0, 50.0))
    coord.upsert_agent(
        AgentStatus("bj-1", 0, 0, 0, soc=0.9, payload_frac=0.0, health_factor=1.0, stamp_s=1.0)
    )
    coord.upsert_agent(
        AgentStatus("bj-2", 90, 0, 0, soc=0.5, payload_frac=0.0, health_factor=1.0, stamp_s=1.0)
    )
    offer = coord.allocate_explore_sector("B7", now_s=1.0)
    assert offer is not None
    # nearer + higher soc should be bj-1
    assert offer.agent_id == "bj-1"
    assert coord.allocate_explore_sector("B7", now_s=1.0) is None  # offer still open

    a1 = SwarmAgent("bj-1")
    a2 = SwarmAgent("bj-2")
    c1 = a1.handle_offer(offer, now_s=1.1)
    c2 = a2.handle_offer(offer, now_s=1.1)
    assert c1 is not None and c1.kind == TaskClaimKind.ACCEPT
    assert c2 is None  # wrong agent_id

    assert coord.on_claim(c1, now_s=1.2) is True
    assert coord._assigned_tasks[offer.task_id] == "bj-1"
