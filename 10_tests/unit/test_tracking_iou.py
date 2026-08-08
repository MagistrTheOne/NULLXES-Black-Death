"""IOU tracker stability tests."""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "06_autonomy"))

from perception.tracking import DetIn, IouTracker


def test_stable_id_across_frames():
    tr = IouTracker(iou_thresh=0.3, max_age=10, min_hits=1)
    d0 = DetIn(0, "human", 0.9, 10, 10, 50, 80)
    t1 = tr.update([d0])
    assert len(t1) == 1
    tid = t1[0].track_id
    d1 = DetIn(0, "human", 0.85, 12, 12, 52, 82)
    t2 = tr.update([d1])
    assert len(t2) == 1
    assert t2[0].track_id == tid


def test_class_mismatch_new_track():
    tr = IouTracker()
    tr.update([DetIn(0, "human", 0.9, 10, 10, 50, 80)])
    t2 = tr.update([DetIn(1, "vehicle", 0.9, 12, 12, 52, 82)])
    assert len(t2) == 1
    assert t2[0].cls_id == 1
