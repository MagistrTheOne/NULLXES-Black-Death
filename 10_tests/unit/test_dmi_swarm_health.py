"""Swarm Health aging tests."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "06_autonomy"))

from dmi.swarm_health import (
    LIMITED_AFTER_S,
    LOST_AFTER_S,
    SwarmHealthState,
    age_health,
    health_to_factor,
)


def test_online_fresh():
    s = age_health(
        previous=SwarmHealthState.ONLINE,
        now_s=10.0,
        last_status_stamp_s=10.0,
        reported_ok=True,
    )
    assert s == SwarmHealthState.ONLINE
    assert health_to_factor(s) == 1.0


def test_limited_then_lost():
    s = age_health(
        previous=SwarmHealthState.ONLINE,
        now_s=10.0 + LIMITED_AFTER_S + 0.1,
        last_status_stamp_s=10.0,
        reported_ok=True,
    )
    assert s == SwarmHealthState.LIMITED
    s2 = age_health(
        previous=s,
        now_s=10.0 + LOST_AFTER_S + 0.1,
        last_status_stamp_s=10.0,
        reported_ok=True,
    )
    assert s2 == SwarmHealthState.LOST


def test_recover_path():
    s = age_health(
        previous=SwarmHealthState.LOST,
        now_s=20.0,
        last_status_stamp_s=20.0,
        reported_ok=True,
    )
    assert s == SwarmHealthState.RECOVERED
    s2 = age_health(
        previous=s,
        now_s=20.1,
        last_status_stamp_s=20.1,
        reported_ok=True,
    )
    assert s2 == SwarmHealthState.ONLINE
