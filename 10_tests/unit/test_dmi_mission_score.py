"""Mission Score unit tests."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "06_autonomy"))

from dmi.mission_score import AgentScoreInput, MissionScoreWeights, score_agent, select_best_agent


def test_closer_higher_soc_wins():
    a = AgentScoreInput("a", distance_m=10.0, soc=0.9, payload_frac=0.1, health_factor=1.0)
    b = AgentScoreInput("b", distance_m=100.0, soc=0.5, payload_frac=0.1, health_factor=1.0)
    sa = score_agent(a, max_distance_m=200.0)
    sb = score_agent(b, max_distance_m=200.0)
    assert sa > sb
    best = select_best_agent([a, b], max_distance_m=200.0)
    assert best is not None
    assert best[0] == "a"


def test_weights_must_sum():
    w = MissionScoreWeights(0.5, 0.5, 0.5, 0.5)
    try:
        score_agent(
            AgentScoreInput("a", 0, 1, 0, 1),
            max_distance_m=10.0,
            weights=w,
        )
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_empty_select():
    assert select_best_agent([], max_distance_m=10.0) is None
