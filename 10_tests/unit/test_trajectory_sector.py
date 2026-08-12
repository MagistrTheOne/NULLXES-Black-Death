"""Lawnmower EXPLORE >1 waypoint; LOITER holds nav.xy + intent.z."""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "06_autonomy"))

from dmi.messages import IntentKind, SwarmIntent
from planning.trajectory import TrajectoryPlanner, lawnmower
from soft_bus.messages import NavStateMsg


def test_lawnmower_more_than_one_wp():
    wps = lawnmower(xmin=0.0, xmax=80.0, ymin=0.0, ymax=80.0, z=50.0, spacing_m=40.0)
    assert len(wps) > 1


def test_explore_sector_path_has_multiple_waypoints():
    p = TrajectoryPlanner()
    p.set_intent(
        SwarmIntent(
            "i1",
            IntentKind.EXPLORE_SECTOR,
            "a1",
            x=40.0,
            y=40.0,
            z=50.0,
            xmin=0.0,
            xmax=80.0,
            ymin=0.0,
            ymax=80.0,
            spacing_m=40.0,
        )
    )
    assert p._path is not None
    assert len(p._path.waypoints) > 1
    g = p.tick(NavStateMsg(x=-10.0, y=-10.0, z=50.0), stamp_s=1.0)
    assert g is not None
    assert g.action == "GOTO_XYZ"


def test_loiter_uses_nav_xy_intent_z():
    p = TrajectoryPlanner()
    p.set_intent(SwarmIntent("i2", IntentKind.LOITER, "a1", x=100.0, y=200.0, z=80.0))
    g = p.tick(NavStateMsg(x=3.0, y=4.0, z=10.0), stamp_s=2.0)
    assert g is not None
    assert g.x == 3.0 and g.y == 4.0 and g.z == 80.0
    assert g.action == "LOITER"


def test_goto_single_waypoint():
    p = TrajectoryPlanner()
    p.set_intent(SwarmIntent("i3", IntentKind.GOTO_XYZ, "a1", x=9.0, y=8.0, z=7.0))
    assert p._path is not None
    assert len(p._path.waypoints) == 1
    g = p.tick(NavStateMsg(x=0.0, y=0.0, z=7.0), stamp_s=1.0)
    assert g is not None
    assert g.x == 9.0 and g.y == 8.0 and g.z == 7.0
