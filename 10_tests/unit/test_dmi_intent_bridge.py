"""Intent → GoalMsg bridge tests."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "06_autonomy"))

from dmi.intent_bridge import intent_to_goal
from dmi.messages import IntentKind, SwarmIntent


def test_explore_to_goal():
    intent = SwarmIntent(
        "i1", IntentKind.EXPLORE_SECTOR, "bj-1", sector_id="B7", x=10, y=20, z=30, stamp_s=1.0
    )
    g = intent_to_goal(intent)
    assert g.x == 10 and g.y == 20 and g.z == 30
