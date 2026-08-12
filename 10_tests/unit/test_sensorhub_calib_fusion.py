"""SensorHub + calib + SceneFusion v2 + ArduPlane + VIO contract tests."""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "06_autonomy"))

from dmi.messages import WorldFact
from l0_bridge.arduplane_adapter import ArduPlaneAdapter, HomeOrigin, PlaneCmdKind
from perception.calibration.loader import load_calib_bundle
from perception.fusion.nav_fuse import fuse_nav_vio
from perception.fusion.scene_fusion import FusionCalib, tracks_to_facts
from perception.sensors.fc_telemetry import FcTelemetry, map_fc_to_bus
from perception.sensors.sensor_hub import SensorHub
from perception.slam.ivio import OpenVinsProvider
from perception.tracking import DetIn, FallbackTracker, Track
from soft_bus.bus import SoftBus
from soft_bus.messages import (
    TOPIC_GNSS,
    TOPIC_IMU,
    TOPIC_NAV,
    TOPIC_SENSORHUB_HEALTH,
    ImageMsg,
    NavStateMsg,
    VioStateMsg,
)


def test_fc_ned_to_enu_mapping():
    fc = FcTelemetry(north_m=10.0, east_m=3.0, down_m=-20.0, yaw_rad=0.0, fix_ok=True)
    imu, gnss, nav = map_fc_to_bus(fc)
    assert gnss.x == 3.0 and gnss.y == 10.0 and gnss.z == 20.0
    assert nav.source == "fc"
    assert imu.frame_id == "enu"


def test_sensorhub_ingest_publishes():
    bus = SoftBus()
    hub = SensorHub(bus)
    seen = {"imu": 0, "gnss": 0, "nav": 0, "health": 0}
    bus.subscribe(TOPIC_IMU, lambda _: seen.__setitem__("imu", seen["imu"] + 1))
    bus.subscribe(TOPIC_GNSS, lambda _: seen.__setitem__("gnss", seen["gnss"] + 1))
    bus.subscribe(TOPIC_NAV, lambda _: seen.__setitem__("nav", seen["nav"] + 1))
    bus.subscribe(TOPIC_SENSORHUB_HEALTH, lambda _: seen.__setitem__("health", seen["health"] + 1))
    hub.ingest_fc(FcTelemetry(fix_ok=True, north_m=1.0, east_m=2.0, down_m=-5.0))
    assert seen["imu"] == 1
    assert seen["gnss"] == 1
    assert seen["nav"] == 1
    assert seen["health"] == 1


def test_calib_bundle_hashes():
    root = REPO / "06_autonomy" / "calib"
    b = load_calib_bundle(root / "camera_forward.yaml", root / "extrinsics.yaml", root / "imu0.yaml")
    assert b.ok
    assert len(b.camera_hash) == 64
    assert b.camera.fx == 500.0


def test_scene_fusion_v2_with_calib_has_finite_cov():
    root = REPO / "06_autonomy" / "calib"
    b = load_calib_bundle(root / "camera_forward.yaml", root / "extrinsics.yaml", root / "imu0.yaml")
    calib = FusionCalib(intrinsics=b.camera, T_body_cam=b.T_body_cam)
    nav = NavStateMsg(x=0, y=0, z=20, yaw=0.0, stamp_s=1.0, cov_xx=1.0, cov_yy=1.0, cov_zz=1.0)
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
    f = facts[0]
    assert f.fact_id == "trk-7"
    assert f.frame_id == "enu"
    assert f.cov_xx < 1.0e5
    assert isinstance(f, WorldFact)


def test_arduplane_goto_not_copter_velocity():
    ad = ArduPlaneAdapter(home=HomeOrigin(50.0, 30.0, 100.0))
    ad.on_heartbeat(mode="GUIDED", armed=True)
    from soft_bus.messages import GoalMsg

    cmd = ad.goal_to_command(GoalMsg(x=100.0, y=50.0, z=30.0, stamp_s=1.0))
    assert cmd.kind == PlaneCmdKind.GOTO_LLA
    payload = ad.to_mavlink_dict(cmd)
    assert payload["type"] == "MISSION_ITEM_INT"
    assert payload["current"] == 2
    assert payload["command"] == 16
    # x=lon*1e7, y=lat*1e7 per Plane docs
    assert payload["x"] == int(cmd.lon_deg * 1e7)
    assert payload["y"] == int(cmd.lat_deg * 1e7)


def test_arduplane_link_lost_hold():
    ad = ArduPlaneAdapter()
    cmd = ad.mark_link_lost()
    assert cmd.kind == PlaneCmdKind.HOLD
    assert ad.health.link_ok is False


def test_fallback_tracker_botsort_then_iou():
    tr = FallbackTracker(budget_ms=0.0001)  # force overbudget → IOU
    d0 = [DetIn(2, "uav", 0.9, 10, 10, 40, 40)]
    t1 = tr.update(d0)
    assert t1
    # after overbudget mode is iou
    t2 = tr.update([DetIn(2, "uav", 0.9, 12, 12, 42, 42)])
    assert t2[0].track_id == t1[0].track_id or tr.mode == "iou"


def test_vio_provider_and_fuse():
    p = OpenVinsProvider()
    p.push_imu(__import__("soft_bus.messages", fromlist=["ImuMsg"]).ImuMsg(stamp_ns=1_000_000))
    img = ImageMsg(bgr=None, stamp_s=1.0, stamp_ns=2_000_000)
    vio = p.push_image(img)
    assert vio is not None
    assert vio.provider == "openvins"
    assert vio.status == "uninit"
    fc = NavStateMsg(x=1, y=2, z=3, cov_xx=4, cov_yy=4, cov_zz=4, source="fc")
    fused = fuse_nav_vio(fc, vio, stamp_s=1.0)
    assert fused.source == "fc"
    assert fused.x == 1.0 and fused.y == 2.0 and fused.z == 3.0
    assert fused.frame_id == "enu"
