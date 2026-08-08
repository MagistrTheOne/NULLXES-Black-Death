"""Scene fusion + analyst tests."""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "06_autonomy"))

from dmi.messages import WorldFact
from perception.calibration.loader import load_calib_bundle
from perception.fusion.scene_analyst import analyze_scene
from perception.fusion.scene_fusion import FusionCalib, tracks_to_facts
from perception.tracking import Track
from soft_bus.messages import NavStateMsg


def test_tracks_to_facts_with_nav():
    root = REPO / "06_autonomy" / "calib"
    bundle = load_calib_bundle(
        root / "camera_forward.yaml",
        root / "extrinsics.yaml",
        root / "imu0.yaml",
    )
    calib = FusionCalib(intrinsics=bundle.camera, T_body_cam=bundle.T_body_cam)
    nav = NavStateMsg(x=0, y=0, z=10, yaw=0.0, stamp_s=1.0, cov_xx=1.0, cov_yy=1.0, cov_zz=1.0)
    tracks = [
        Track(
            track_id=7,
            cls_id=2,
            name="uav",
            conf=0.8,
            x1=300,
            y1=200,
            x2=340,
            y2=240,
            age=2,
            hits=2,
            time_since_update=0,
        )
    ]
    facts = tracks_to_facts(tracks, nav, calib=calib, stamp_s=1.0)
    assert len(facts) == 1
    assert facts[0].fact_id == "trk-7"
    assert facts[0].kind == "uav"
    assert facts[0].confidence == 0.8
    assert facts[0].frame_id == "enu"
    assert facts[0].cov_xx < 1.0e5


def test_analyst_uav_critical_no_link_loiter():
    facts = [
        WorldFact("trk-1", "uav", 10, 0, 5, 0.9, "a", 1.0),
    ]
    a = analyze_scene(facts, stamp_s=1.0, link_ok=False)
    assert a.suggested_intent_kind == "LOITER"
    assert any(x.severity == "critical" for x in a.alerts)


def test_analyst_clear():
    a = analyze_scene([], stamp_s=1.0, link_ok=True)
    assert a.summary == "scene clear"
