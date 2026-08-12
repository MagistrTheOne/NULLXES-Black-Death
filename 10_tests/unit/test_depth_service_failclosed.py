"""DepthService — fail-closed until a real depth ORT decoder exists."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "06_autonomy"))

from perception.depth.depth_service import DepthService
from soft_bus.messages import ImageMsg


def test_depth_ok_false_empty_cells():
    svc = DepthService(min_period_s=-1.0)
    out = svc.step(ImageMsg(bgr=np.zeros((16, 16, 3), dtype=np.uint8), stamp_ns=1))
    assert out is not None
    assert out.ok is False
    assert out.cells == []
