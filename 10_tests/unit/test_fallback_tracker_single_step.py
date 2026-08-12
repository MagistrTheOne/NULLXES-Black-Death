"""BoT-SORT KF + Byte two-stage; overrun keeps this frame primary, next frame IOU."""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "06_autonomy"))

from perception.tracking import BotSortTracker, DetIn, FallbackTracker


def test_overrun_this_frame_primary_next_iou():
    tr = FallbackTracker(budget_ms=0.0, use_cmc=False)
    calls = {"p": 0, "f": 0}
    orig_p = tr.primary.update
    orig_f = tr.fallback.update

    def _p(dets, **kw):
        calls["p"] += 1
        return orig_p(dets, **kw)

    def _f(dets, **kw):
        calls["f"] += 1
        return orig_f(dets, **kw)

    tr.primary.update = _p
    tr.fallback.update = _f
    d0 = [DetIn(2, "uav", 0.9, 10, 10, 40, 40)]
    t1 = tr.update(d0)
    assert t1
    assert calls == {"p": 1, "f": 0}
    assert tr.mode == "iou"
    t2 = tr.update([DetIn(2, "uav", 0.9, 12, 12, 42, 42)])
    assert t2
    assert calls["p"] == 1
    assert calls["f"] == 1


def test_kf_velocity_after_motion():
    tr = BotSortTracker(use_cmc=False)
    tr.update([DetIn(0, "human", 0.9, 10, 10, 50, 80)])
    tr.update([DetIn(0, "human", 0.9, 20, 10, 60, 80)])
    assert len(tr._tracks) == 1
    assert tr._tracks[0].vx != 0.0


def test_byte_low_conf_second_stage():
    tr = BotSortTracker(use_cmc=False, high_conf=0.5, iou_thresh=0.3, low_iou_thresh=0.15)
    t1 = tr.update([DetIn(0, "human", 0.9, 10, 10, 50, 80)])
    tid = t1[0].track_id
    t2 = tr.update([DetIn(0, "human", 0.2, 12, 12, 52, 82)])
    assert len(t2) == 1
    assert t2[0].track_id == tid
