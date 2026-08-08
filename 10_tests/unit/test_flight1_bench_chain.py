"""FLIGHT-1 software birth chain (no physical HW required)."""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "06_autonomy"))

from tools.flight1_bench_chain import run_bench


def test_flight1_bench_chain_ok():
    report = run_bench()
    assert report["ok"] is True
    assert report["kind"] == "uav"
    assert report["frame_id"] == "enu"
    assert report["plane_cmd"] is not None
    assert report["plane_cmd"]["type"] == "MISSION_ITEM_INT"
    assert report["calib_ok"] is True
