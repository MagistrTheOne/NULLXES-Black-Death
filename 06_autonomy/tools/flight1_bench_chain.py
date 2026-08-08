#!/usr/bin/env python3
"""FLIGHT-1 props-off software chain: SensorHub→Track→WorldFact→DMI→Plane cmd.

Physical cam/H743 optional. Without HW, injects FC telemetry + synthetic frame
through the same SensorHub / VisionFacts contracts (no webcam-script bypass).
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "06_autonomy"))

from dmi.intent_bridge import intent_to_goal
from dmi.messages import TOPIC_DMI_WORLD_FACT, IntentKind, SwarmIntent, WorldFact
from l0_bridge.arduplane_adapter import HomeOrigin
from perception.sensors.fc_telemetry import FcTelemetry
from ros2.nodes.calib_soft import CalibSoftNode
from ros2.nodes.l0_bridge_soft import L0BridgeSoftNode
from ros2.nodes.sensor_hub_soft import SensorHubSoftNode
from ros2.nodes.vision_facts_soft import VisionFactsSoftNode
from soft_bus.bus import SoftBus
from soft_bus.messages import (
    TOPIC_DETECTIONS,
    TOPIC_GOAL,
    TOPIC_PLANE_CMD,
    TOPIC_SCENE,
    Detection,
    DetectionArray,
    SceneAssessment,
)


def run_bench(*, with_camera: int | None = None) -> dict:
    bus = SoftBus()
    CalibSoftNode(bus)
    hub = SensorHubSoftNode(bus, camera_device=with_camera)
    VisionFactsSoftNode(bus, enable_poseidon=False, link_ok=True, use_botsort=True)
    bridge = L0BridgeSoftNode(
        bus,
        home=HomeOrigin(lat_deg=50.0, lon_deg=30.0, alt_amsl_m=100.0),
    )
    bridge.on_heartbeat(mode="GUIDED", armed=False)

    # FC local NED sample → ENU nav via SensorHub
    hub.ingest_fc(
        FcTelemetry(
            yaw_rad=0.0,
            north_m=0.0,
            east_m=0.0,
            down_m=-20.0,
            fix_ok=True,
            hdop=1.0,
            time_boot_ms=1000,
            sensor_stamp_ns=1_000_000_000,
        )
    )
    hub.pulse()

    facts: list[WorldFact] = []
    scenes: list[SceneAssessment] = []
    cmds: list[dict] = []
    bus.subscribe(TOPIC_DMI_WORLD_FACT, facts.append)
    bus.subscribe(TOPIC_SCENE, scenes.append)
    bus.subscribe(TOPIC_PLANE_CMD, cmds.append)

    # Inject CERBER detection (physical detector may replace this on Orin)
    bus.publish(
        TOPIC_DETECTIONS,
        DetectionArray(
            detections=[Detection(2, 0.91, 300, 200, 340, 240)],
            camera="forward",
            stamp_s=time.time(),
        ),
    )

    if not facts:
        return {"ok": False, "error": "no WorldFact"}

    fact = facts[0]
    intent = SwarmIntent(
        intent_id="bench-1",
        kind=IntentKind.GOTO_XYZ,
        agent_id="alpha",
        x=fact.x,
        y=fact.y,
        z=fact.z,
        stamp_s=time.time(),
    )
    goal = intent_to_goal(intent)
    bus.publish(TOPIC_GOAL, goal)

    hub.stop()
    return {
        "ok": True,
        "fact_id": fact.fact_id,
        "kind": fact.kind,
        "enu": [fact.x, fact.y, fact.z],
        "cov": [fact.cov_xx, fact.cov_yy, fact.cov_zz],
        "frame_id": fact.frame_id,
        "scene": scenes[0].summary if scenes else "",
        "plane_cmd": cmds[-1] if cmds else None,
        "calib_ok": bool(bus.latest("/bd/calib/active") and bus.latest("/bd/calib/active").ok),
    }


def main() -> int:
    report = run_bench()
    print(json.dumps(report, indent=2))
    return 0 if report.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
