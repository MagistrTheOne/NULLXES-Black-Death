"""Unit tests for vision preprocess."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "06_autonomy"))

from perception.vision.preprocess import bgr_to_nchw_float, letterbox


def test_letterbox_shape():
    img = np.zeros((480, 640, 3), dtype=np.uint8)
    out, ratio, pad = letterbox(img, (640, 640))
    assert out.shape == (640, 640, 3)
    assert ratio > 0
    assert pad[0] >= 0 and pad[1] >= 0


def test_nchw():
    img = np.zeros((640, 640, 3), dtype=np.uint8)
    t = bgr_to_nchw_float(img)
    assert t.shape == (1, 3, 640, 640)
    assert t.dtype == np.float32
