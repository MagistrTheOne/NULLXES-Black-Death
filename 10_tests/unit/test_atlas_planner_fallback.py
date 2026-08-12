"""ATLAS planner without STABLE ONNX uses Mission Score — never random."""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "06_autonomy"))

from atlas.messages import CopAgent, CopSector, CopSnapshot
from atlas.planner import AtlasPlanner
from atlas.runtime import pack_is_stable
from dmi.mission_score import AgentScoreInput, select_best_agent


def test_candidate_pack_not_stable():
    pack = REPO / "06_autonomy" / "models" / "atlas" / "packs" / "atlas_alloc_v1" / "pack.yaml"
    assert pack.is_file()
    assert pack_is_stable(pack) is False


def test_planner_matches_mission_score_not_random():
    planner = AtlasPlanner()
    assert planner.using_onnx is False
    snap = CopSnapshot(
        agents=[
            CopAgent("bj-far", 400.0, 0.0, 50.0, 0.4, 0.2, 0.8),
            CopAgent("bj-near", 10.0, 0.0, 50.0, 0.95, 0.0, 1.0),
        ],
        sectors=[CopSector("B7", 0.0, 0.0, 50.0)],
        stamp_s=1.0,
    )
    p1 = planner.plan(snap)
    p2 = planner.plan(snap)
    assert len(p1.assignments) == 1
    assert p1.assignments[0].agent_id == p2.assignments[0].agent_id == "bj-near"
    cands = [
        AgentScoreInput("bj-far", 400.0, 0.4, 0.2, 0.8),
        AgentScoreInput("bj-near", 10.0, 0.95, 0.0, 1.0),
    ]
    best = select_best_agent(cands, max_distance_m=500.0)
    assert best is not None
    assert p1.assignments[0].agent_id == best[0]
    assert p1.model == "BLACK-ATLAS-ALLOC-01"
