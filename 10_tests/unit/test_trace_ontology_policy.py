"""Trace + WorldObject ontology + MissionPolicy gate."""

from __future__ import annotations

import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "06_autonomy"))

from dmi.intent_bridge import intent_to_goal_gated
from dmi.messages import (
    TOPIC_DMI_WORLD_OBJECT,
    IntentKind,
    SwarmIntent,
    WorldFact,
)
from dmi.mission_policy import MissionPolicyGate, load_mission_profile
from dmi.world_cache import SharedWorldCache
from perception.fusion.scene_fusion import fact_to_world_object
from perception.trace.recorder import FlightRecorder, new_trace_id
from poseidon.pack_spec import PackSpecError, load_pack_spec
from ros2.nodes.vision_facts_soft import VisionFactsSoftNode
from soft_bus.bus import SoftBus
from soft_bus.messages import (
    TOPIC_DETECTIONS,
    TOPIC_NAV,
    TOPIC_TRACE_SPAN,
    Detection,
    DetectionArray,
    NavStateMsg,
    TraceSpan,
)


def test_flight_recorder_spans():
    bus = SoftBus()
    spans: list[TraceSpan] = []
    bus.subscribe(TOPIC_TRACE_SPAN, spans.append)
    rec = FlightRecorder(bus, agent_id="t")
    tid = new_trace_id("t")
    with rec.span("sensorhub", trace_id=tid):
        pass
    with rec.span("cerber", trace_id=tid):
        pass
    assert len(spans) == 2
    assert spans[0].trace_id == spans[1].trace_id == tid
    assert spans[0].stage == "sensorhub"


def test_world_object_cache_merge():
    c = SharedWorldCache()
    f = WorldFact("trk-1", "uav", 1, 2, 3, 0.8, "a", stamp_s=1.0, track_id=1, trace_id="tr")
    obj = fact_to_world_object(f)
    changed, stored = c.upsert_object(obj, now_s=1.0)
    assert changed
    assert stored.first_seen_s == 1.0
    f2 = WorldFact("trk-1", "uav", 1.5, 2, 3, 0.9, "a", stamp_s=2.0, track_id=1)
    obj2 = fact_to_world_object(f2, attrs={"attr_unknown": "true"})
    changed2, stored2 = c.upsert_object(obj2, now_s=2.0)
    assert changed2
    assert stored2.first_seen_s == 1.0
    assert stored2.last_seen_s >= 2.0
    assert stored2.attrs.get("attr_unknown") == "true"
    assert stored2.state == "confirmed"


def test_mission_policy_gate_deny_chase():
    path = REPO / "06_autonomy" / "mission_profiles" / "inspection.powerline.v1.yaml"
    profile = load_mission_profile(path)
    gate = MissionPolicyGate(profile)
    intent = SwarmIntent("i1", IntentKind.GOTO_XYZ, "a1", x=10, y=10, z=50, stamp_s=1.0)
    goal, dec = intent_to_goal_gated(intent, gate, stamp_s=1.0)
    assert goal is not None
    assert dec.allowed
    # CHASE not an IntentKind — gate.allow_action directly
    deny = gate.allow_action("CHASE", stamp_s=1.0)
    assert deny.allowed is False
    assert "denied" in deny.reason or "not_allowed" in deny.reason


def test_mission_policy_geofence():
    path = REPO / "06_autonomy" / "mission_profiles" / "perimeter.alert.v1.yaml"
    gate = MissionPolicyGate(load_mission_profile(path))
    dec = gate.allow_action("GOTO_XYZ", x=9000, y=0, z=50, stamp_s=1.0)
    assert dec.allowed is False
    assert dec.reason == "geofence"


def test_vision_facts_emits_trace_and_world_object():
    bus = SoftBus()
    spans: list[TraceSpan] = []
    objects = []
    bus.subscribe(TOPIC_TRACE_SPAN, spans.append)
    bus.subscribe(TOPIC_DMI_WORLD_OBJECT, objects.append)
    VisionFactsSoftNode(bus, enable_poseidon=False, link_ok=True)
    tid = new_trace_id("vf")
    bus.publish(TOPIC_NAV, NavStateMsg(x=0, y=0, z=20, yaw=0.0, stamp_s=time.time(), cov_xx=1, cov_yy=1, cov_zz=1))
    bus.publish(
        TOPIC_DETECTIONS,
        DetectionArray(
            detections=[Detection(2, 0.9, 300, 200, 340, 240)],
            stamp_s=time.time(),
            trace_id=tid,
        ),
    )
    assert objects
    assert objects[0].type == "uav"
    assert objects[0].trace_id == tid
    stages = {s.stage for s in spans}
    assert "track" in stages and "fusion" in stages and "ontology" in stages


def test_pack_spec_stable_pending_blocked(tmp_path: Path):
    p = tmp_path / "pack.yaml"
    p.write_text(
        """
pack_id: bad_stable
dataset: x
onnx_layout: yolo_v8_raw
model_path: model.onnx
sha256: pending
input_size: [640, 640]
classes: [uav]
cerber_remap: {0: 2}
release_channel: STABLE
required: false
""",
        encoding="utf-8",
    )
    try:
        load_pack_spec(p)
        assert False, "expected PackSpecError"
    except PackSpecError as e:
        assert "STABLE" in str(e)


def test_seg_and_vehicle_attr_packs_load():
    for pack in ("scene_segformer_b0", "vehicle_attr_lowagl"):
        spec = load_pack_spec(
            REPO / "06_autonomy" / "models" / "poseidon" / "packs" / pack / "pack.yaml"
        )
        assert spec.release_channel == "CANDIDATE"
        assert spec.sha256 == ""
