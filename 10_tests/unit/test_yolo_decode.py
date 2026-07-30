"""Unit tests — YOLO_V8_RAW decode + NMS (algorithm only)."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "06_autonomy"))

from perception.vision.decode import Detection, decode_yolo_v8_raw
from perception.vision.layout import UnsupportedLayoutError
from perception.vision.nms import nms


def test_decode_yolo_v8_raw_one_box():
    nc = 5
    n = 10
    pred = np.zeros((1, 4 + nc, n), dtype=np.float32)
    pred[0, 0, 0] = 320.0
    pred[0, 1, 0] = 320.0
    pred[0, 2, 0] = 100.0
    pred[0, 3, 0] = 80.0
    pred[0, 4, 0] = 0.95
    dets = decode_yolo_v8_raw(
        pred,
        num_classes=nc,
        conf_thres=0.35,
        ratio=1.0,
        pad_x=0,
        pad_y=0,
        orig_hw=(640, 640),
    )
    assert len(dets) == 1
    assert dets[0].cls_id == 0
    assert dets[0].conf >= 0.9
    assert dets[0].x1 < dets[0].x2


def test_decode_rejects_wrong_c():
    pred = np.zeros((1, 8, 5), dtype=np.float32)  # expect 9 for nc=5
    with pytest.raises(UnsupportedLayoutError):
        decode_yolo_v8_raw(
            pred,
            num_classes=5,
            conf_thres=0.35,
            ratio=1.0,
            pad_x=0,
            pad_y=0,
            orig_hw=(640, 640),
        )


def test_decode_rejects_transpose_guess_shape():
    # [1, N, C] is not YOLO_V8_RAW
    pred = np.zeros((1, 10, 9), dtype=np.float32)
    with pytest.raises(UnsupportedLayoutError):
        decode_yolo_v8_raw(
            pred,
            num_classes=5,
            conf_thres=0.35,
            ratio=1.0,
            pad_x=0,
            pad_y=0,
            orig_hw=(640, 640),
        )


def test_decode_filters_low_conf():
    pred = np.zeros((1, 9, 5), dtype=np.float32)
    pred[0, 4, 0] = 0.1
    dets = decode_yolo_v8_raw(
        pred,
        num_classes=5,
        conf_thres=0.35,
        ratio=1.0,
        pad_x=0,
        pad_y=0,
        orig_hw=(640, 640),
    )
    assert dets == []


def test_nms_suppresses_overlap():
    a = Detection(0, 0.9, 0, 0, 10, 10)
    b = Detection(0, 0.8, 1, 1, 11, 11)
    c = Detection(1, 0.85, 0, 0, 10, 10)
    out = nms([a, b, c], iou_thres=0.5)
    assert len(out) == 2
    assert {d.cls_id for d in out} == {0, 1}
