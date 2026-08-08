"""Civil track guidance — chase/escort/deny."""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "06_autonomy"))

from control.guidance.simple_guidance import NavState
from control.guidance.track_guidance import goal_from_track_mode, track_guidance


def test_chase_standoff():
    nav = NavState(0, 0, 10, 0, 0, 0, 0)
    gx, gy, gz = goal_from_track_mode(nav, 100, 0, 10, "chase")
    assert gx < 100
    assert abs(gy) < 1e-6


def test_deny_holds_outside():
    nav = NavState(0, 0, 10, 0, 0, 0, 0)
    gx, gy, _ = goal_from_track_mode(nav, 10, 0, 10, "deny")
    # target close → push out to deny radius
    assert gx <= 10


def test_track_guidance_valid():
    nav = NavState(0, 0, 10, 0, 0, 0, 0)
    out = track_guidance(nav, 50, 0, 10, "escort")
    assert out.valid
