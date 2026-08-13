"""S1 energy arcade — stall / launch / no hover. Not X8 proof."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "07_simulation" / "bd_sim"))

from sim.vehicle import Vehicle  # noqa: E402


def test_ground_no_hover_without_launch():
    v = Vehicle()
    v.step(0.01, pitch_cmd=0, roll_cmd=0, yaw_cmd=0, throttle_cmd=1.0, launch=False)
    assert v.state.launched is False
    assert v.state.z <= 0.4
    assert v.state.airspeed == 0.0


def test_launch_then_airspeed():
    v = Vehicle()
    flags = v.step(0.01, pitch_cmd=0, roll_cmd=0, yaw_cmd=0, throttle_cmd=0.5, launch=True)
    assert "LAUNCH" in flags
    assert v.state.launched is True
    for _ in range(200):
        v.step(0.01, pitch_cmd=0.05, roll_cmd=0.0, yaw_cmd=0, throttle_cmd=0.4, launch=False)
    assert v.state.airspeed > 5.0
    assert v.state.crashed is False
