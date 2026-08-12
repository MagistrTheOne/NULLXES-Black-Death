"""SegFormerService — real ORT session or fail-closed ok=False."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "06_autonomy"))

from perception.segmentation.segformer_service import SEG_CLASSES, SegFormerService
from soft_bus.messages import ImageMsg


def _img() -> ImageMsg:
    return ImageMsg(bgr=np.zeros((32, 32, 3), dtype=np.uint8), stamp_s=1.0, stamp_ns=1)


def test_no_session_ok_false():
    svc = SegFormerService(min_period_s=-1.0)
    out = svc.step(_img())
    assert out is not None
    assert out.ok is False
    assert out.classes_present == []


class _OrtOk:
    def run(self, _outs, feeds):
        x = feeds["input"]
        assert x.ndim == 4 and x.shape[1] == 3 and x.shape[2] == 512 and x.shape[3] == 512
        logits = np.zeros((1, len(SEG_CLASSES), 512, 512), dtype=np.float32)
        logits[0, 6] = 8.0
        return [logits]


def test_session_argmax_classes():
    svc = SegFormerService(min_period_s=-1.0, session=_OrtOk())
    out = svc.step(_img())
    assert out is not None
    assert out.ok is True
    assert "safe_terrain" in out.classes_present


class _OrtBadShape:
    def run(self, _outs, _feeds):
        return [np.array([1.0], dtype=np.float32)]


def test_shape_fail_ok_false():
    svc = SegFormerService(min_period_s=-1.0, session=_OrtBadShape())
    out = svc.step(_img())
    assert out is not None
    assert out.ok is False
    assert out.classes_present == []
