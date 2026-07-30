"""Shared World Cache tests."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "06_autonomy"))

from dmi.messages import WorldFact
from dmi.world_cache import SharedWorldCache


def test_upsert_and_ttl():
    c = SharedWorldCache(ttl_s=1.0)
    f = WorldFact("t1", "tree", 1, 2, 3, 0.8, "a", stamp_s=0.0)
    assert c.upsert(f, now_s=0.0) is True
    assert c.get("t1", now_s=0.5) is not None
    assert c.get("t1", now_s=1.5) is None


def test_confidence_merge():
    c = SharedWorldCache(ttl_s=10.0)
    c.upsert(WorldFact("o1", "obstacle", 0, 0, 0, 0.5, "a", 1.0), now_s=1.0)
    changed = c.upsert(WorldFact("o1", "obstacle", 0, 0, 0, 0.9, "b", 1.0), now_s=1.0)
    assert changed is True
    got = c.get("o1", now_s=1.0)
    assert got is not None
    assert got.confidence == 0.9
