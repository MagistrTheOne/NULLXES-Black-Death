"""Unit tests for dual-compute election."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "06_autonomy"))

from core.dual_compute.active_election import ActiveElection, ElectionConfig


def test_prefer_a_when_both_alive():
    el = ActiveElection(ElectionConfig(prefer="A"))
    assert el.step(True, True) == "A"


def test_failover_to_b():
    el = ActiveElection(ElectionConfig(prefer="A", sticky_after_failover=True))
    assert el.step(False, True) == "B"
    assert el.step(True, True) == "B"  # sticky
    assert el.maybe_restore(True, True) == "B"


def test_both_dead_keeps_last():
    el = ActiveElection(ElectionConfig(prefer="A"))
    el.step(False, True)
    assert el.step(False, False) == "B"
