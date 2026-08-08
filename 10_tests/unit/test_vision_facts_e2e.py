"""Host E2E: detections → tracks → WorldFact → scene (no ONNX required)."""

from __future__ import annotations

import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "06_autonomy"))

from dmi.messages import TOPIC_DMI_WORLD_FACT, WorldFact
from ros2.nodes.vision_facts_soft import VisionFactsSoftNode
from soft_bus.bus import SoftBus
from soft_bus.messages import (
    TOPIC_DETECTIONS,
    TOPIC_NAV,
    TOPIC_SCENE,
    TOPIC_TRACKS,
    Detection,
    DetectionArray,
    NavStateMsg,
    SceneAssessment,
    TrackArray,
)


def test_vision_facts_pipeline():
    bus = SoftBus()
    node = VisionFactsSoftNode(bus, enable_poseidon=False, link_ok=True)
    facts: list[WorldFact] = []
    scenes: list[SceneAssessment] = []
    tracks: list[TrackArray] = []
    bus.subscribe(TOPIC_DMI_WORLD_FACT, facts.append)
    bus.subscribe(TOPIC_SCENE, scenes.append)
    bus.subscribe(TOPIC_TRACKS, tracks.append)

    bus.publish(TOPIC_NAV, NavStateMsg(x=0, y=0, z=20, yaw=0.0, stamp_s=time.time()))
    bus.publish(
        TOPIC_DETECTIONS,
        DetectionArray(
            detections=[Detection(2, 0.88, 300, 200, 340, 240)],
            camera="forward",
            stamp_s=time.time(),
        ),
    )

    assert len(tracks) == 1
    assert tracks[0].tracks[0].cls_id == 2
    assert len(facts) == 1
    assert facts[0].kind == "uav"
    assert len(scenes) == 1
    assert scenes[0].alerts
    assert node.all_facts()


def test_no_link_degrade_suggests_loiter():
    bus = SoftBus()
    VisionFactsSoftNode(bus, enable_poseidon=False, link_ok=False)
    scenes: list[SceneAssessment] = []
    bus.subscribe(TOPIC_SCENE, scenes.append)
    bus.publish(TOPIC_NAV, NavStateMsg(x=0, y=0, z=20, yaw=0.0, stamp_s=1.0))
    bus.publish(
        TOPIC_DETECTIONS,
        DetectionArray(
            detections=[Detection(2, 0.9, 300, 200, 340, 240)],
            stamp_s=1.0,
        ),
    )
    assert scenes[0].suggested_intent_kind == "LOITER"
