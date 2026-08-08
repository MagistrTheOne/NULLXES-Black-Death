"""Vision → Track → Fusion → WorldFact + SceneAssessment (+ optional POSEIDON).

No-link: still publishes local facts/scene; GSC optional (ADR-002/004).
"""

from __future__ import annotations

import time
from pathlib import Path

from dmi.messages import TOPIC_DMI_WORLD_FACT, WorldFact
from dmi.world_cache import SharedWorldCache
from perception.fusion.scene_analyst import analyze_scene
from perception.fusion.scene_fusion import CERBER_NAMES, tracks_to_facts
from perception.tracking import DetIn, IouTracker
from soft_bus.bus import SoftBus
from soft_bus.messages import (
    TOPIC_DETECTIONS,
    TOPIC_NAV,
    TOPIC_POSEIDON_ACTIVE,
    TOPIC_POSEIDON_DETECTIONS,
    TOPIC_SCENE,
    TOPIC_TRACKS,
    Detection as BusDet,
    DetectionArray,
    NavStateMsg,
    PoseidonActivePacks,
    PoseidonPackStatus,
    SceneAssessment,
    TrackArray,
    TrackMsg,
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


class VisionFactsSoftNode:
    def __init__(
        self,
        bus: SoftBus,
        *,
        source_id: str = "companion",
        enable_poseidon: bool = True,
        mission_mode: str = "NOMINAL",
        link_ok: bool = True,
    ) -> None:
        self.bus = bus
        self.source_id = source_id
        self.mission_mode = mission_mode
        self.link_ok = link_ok
        self.tracker = IouTracker()
        self.cache = SharedWorldCache()
        self._nav: NavStateMsg | None = None
        self._poseidon = None
        if enable_poseidon:
            try:
                from poseidon.runtime import PoseidonRuntime

                root = _repo_root()
                self._poseidon = PoseidonRuntime(
                    packs_root=root / "06_autonomy" / "models" / "poseidon" / "packs",
                    router_yaml=root
                    / "06_autonomy"
                    / "models"
                    / "poseidon"
                    / "router"
                    / "router.yaml",
                )
            except Exception:
                self._poseidon = None

        bus.subscribe(TOPIC_DETECTIONS, self._on_detections)
        bus.subscribe(TOPIC_NAV, self._on_nav)

    def set_link_ok(self, ok: bool) -> None:
        self.link_ok = ok

    def set_mission_mode(self, mode: str) -> None:
        self.mission_mode = mode

    def _on_nav(self, nav: NavStateMsg) -> None:
        self._nav = nav

    def _on_detections(self, arr: DetectionArray) -> None:
        now = time.time()
        stamp = arr.stamp_s or now
        dets = list(arr.detections)

        # Optional POSEIDON pass requires image — specialist path is bus-side only
        # when poseidon detections published separately; merge if present in same tick
        # via TOPIC_POSEIDON_DETECTIONS latest.
        poseidon_arr = self.bus.latest(TOPIC_POSEIDON_DETECTIONS)
        if isinstance(poseidon_arr, DetectionArray):
            dets = dets + list(poseidon_arr.detections)

        det_ins = [
            DetIn(
                cls_id=d.cls_id,
                name=CERBER_NAMES[d.cls_id]
                if 0 <= d.cls_id < len(CERBER_NAMES)
                else str(d.cls_id),
                conf=d.conf,
                x1=d.x1,
                y1=d.y1,
                x2=d.x2,
                y2=d.y2,
            )
            for d in dets
        ]
        tracks = self.tracker.update(det_ins)
        self.bus.publish(
            TOPIC_TRACKS,
            TrackArray(
                tracks=[
                    TrackMsg(
                        track_id=t.track_id,
                        cls_id=t.cls_id,
                        conf=t.conf,
                        x1=t.x1,
                        y1=t.y1,
                        x2=t.x2,
                        y2=t.y2,
                        age=t.age,
                        hits=t.hits,
                    )
                    for t in tracks
                ],
                camera=arr.camera,
                stamp_s=stamp,
            ),
        )

        facts = tracks_to_facts(
            tracks, self._nav, source_id=self.source_id, stamp_s=stamp
        )
        for fact in facts:
            self.cache.upsert(fact, now_s=now)
            self.bus.publish(TOPIC_DMI_WORLD_FACT, fact)

        assessment = analyze_scene(facts, stamp_s=stamp, link_ok=self.link_ok)
        self.bus.publish(TOPIC_SCENE, assessment)

    def ingest_image_poseidon(self, bgr, cerber_dets: list[BusDet]) -> None:
        """Companion path: run POSEIDON on frame using CERBER hints."""
        if self._poseidon is None:
            return
        from poseidon.router import RouterContext

        max_conf: dict[int, float] = {}
        cls_ids: list[int] = []
        for d in cerber_dets:
            cls_ids.append(d.cls_id)
            max_conf[d.cls_id] = max(max_conf.get(d.cls_id, 0.0), float(d.conf))
        ctx = RouterContext(
            mission_mode=self.mission_mode,
            cerber_cls_ids=cls_ids,
            cerber_max_conf=max_conf,
            link_ok=self.link_ok,
        )
        step = self._poseidon.step(bgr, ctx)
        now = time.time()
        self.bus.publish(
            TOPIC_POSEIDON_DETECTIONS,
            DetectionArray(
                detections=[
                    BusDet(d.cls_id, d.conf, d.x1, d.y1, d.x2, d.y2)
                    for d in step.specialist
                ],
                camera="forward",
                stamp_s=now,
            ),
        )
        self.bus.publish(
            TOPIC_POSEIDON_ACTIVE,
            PoseidonActivePacks(
                packs=[
                    PoseidonPackStatus(r.pack_id, r.latency_ms, len(r.detections))
                    for r in step.pack_runs
                ],
                stamp_s=now,
            ),
        )

    def all_facts(self) -> list[WorldFact]:
        return self.cache.all_facts(now_s=time.time())


def main(bus: SoftBus | None = None) -> SoftBus:
    bus = bus or SoftBus()
    VisionFactsSoftNode(bus)
    return bus


if __name__ == "__main__":
    main()
