"""Vision → Track → Fusion → WorldFact/WorldObject + SceneAssessment (+ optional POSEIDON).

No-link: still publishes local facts/scene; GSC optional (ADR-002/004).
"""

from __future__ import annotations

import time
from dataclasses import replace
from pathlib import Path

from dmi.messages import (
    TOPIC_DMI_EVENT,
    TOPIC_DMI_WORLD_FACT,
    TOPIC_DMI_WORLD_OBJECT,
    OntologyEvent,
    WorldFact,
)
from dmi.world_cache import SharedWorldCache
from perception.fusion.scene_analyst import analyze_scene
from perception.fusion.scene_fusion import CERBER_NAMES, FusionCalib, fact_to_world_object, tracks_to_facts
from perception.trace.recorder import FlightRecorder, new_trace_id
from perception.tracking import DetIn, FallbackTracker, IouTracker
from soft_bus.bus import SoftBus
from soft_bus.messages import (
    TOPIC_CAM_FORWARD,
    TOPIC_DETECTIONS,
    TOPIC_NAV,
    TOPIC_NAV_FUSED,
    TOPIC_POSEIDON_ACTIVE,
    TOPIC_POSEIDON_DETECTIONS,
    TOPIC_POSEIDON_VE_HITS,
    TOPIC_POSEIDON_VL_SCENE,
    TOPIC_SCENE,
    TOPIC_TRACKS,
    ConceptHitArray,
    Detection as BusDet,
    DetectionArray,
    ImageMsg,
    NavStateMsg,
    PoseidonActivePacks,
    PoseidonPackStatus,
    SceneAssessment,
    TrackArray,
    TrackMsg,
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _load_fusion_calib() -> FusionCalib | None:
    try:
        from perception.calibration.loader import load_calib_bundle

        root = _repo_root() / "06_autonomy" / "calib"
        bundle = load_calib_bundle(
            root / "camera_forward.yaml",
            root / "extrinsics.yaml",
            root / "imu0.yaml",
        )
        return FusionCalib(
            intrinsics=bundle.camera,
            T_body_cam=bundle.T_body_cam,
            td_cam_imu_s=bundle.td_cam_imu_s,
        )
    except Exception:
        return None


class VisionFactsSoftNode:
    def __init__(
        self,
        bus: SoftBus,
        *,
        source_id: str = "companion",
        enable_poseidon: bool = True,
        mission_mode: str = "NOMINAL",
        link_ok: bool = True,
        use_botsort: bool = True,
        prefer_fused_nav: bool = True,
        recorder: FlightRecorder | None = None,
    ) -> None:
        self.bus = bus
        self.source_id = source_id
        self.mission_mode = mission_mode
        self.link_ok = link_ok
        self.prefer_fused_nav = prefer_fused_nav
        self.tracker = FallbackTracker() if use_botsort else IouTracker()
        self.cache = SharedWorldCache()
        self.recorder = recorder or FlightRecorder(bus, agent_id=source_id)
        self._nav: NavStateMsg | None = None
        self._frame: object | None = None
        self._calib = _load_fusion_calib()
        self._poseidon = None
        self._semantic = None
        if enable_poseidon:
            try:
                from poseidon.runtime import PoseidonRuntime
                from poseidon.semantic import PoseidonSemanticRuntime

                root = _repo_root()
                packs = root / "06_autonomy" / "models" / "poseidon" / "packs"
                router = (
                    root
                    / "06_autonomy"
                    / "models"
                    / "poseidon"
                    / "router"
                    / "router.yaml"
                )
                self._poseidon = PoseidonRuntime(packs_root=packs, router_yaml=router)
                self._semantic = PoseidonSemanticRuntime(
                    packs_root=packs, router_yaml=router, repo_root=root
                )
            except Exception:
                self._poseidon = None
                self._semantic = None

        bus.subscribe(TOPIC_DETECTIONS, self._on_detections)
        bus.subscribe(TOPIC_NAV, self._on_nav)
        bus.subscribe(TOPIC_NAV_FUSED, self._on_fused)
        bus.subscribe(TOPIC_CAM_FORWARD, self._on_cam)

    def set_link_ok(self, ok: bool) -> None:
        self.link_ok = ok

    def set_mission_mode(self, mode: str) -> None:
        self.mission_mode = mode

    def _on_nav(self, nav: NavStateMsg) -> None:
        if not self.prefer_fused_nav or self._nav is None or self._nav.source != "fused":
            self._nav = nav

    def _on_fused(self, nav: NavStateMsg) -> None:
        if self.prefer_fused_nav:
            self._nav = nav

    def _on_cam(self, img: ImageMsg) -> None:
        self._frame = img.bgr

    def _on_detections(self, arr: DetectionArray) -> None:
        now = time.time()
        stamp = arr.stamp_s or now
        trace_id = arr.trace_id or new_trace_id(self.source_id)
        dets = list(arr.detections)

        poseidon_arr = self.bus.latest(TOPIC_POSEIDON_DETECTIONS)
        if isinstance(poseidon_arr, DetectionArray):
            dets = dets + list(poseidon_arr.detections)

        with self.recorder.span("track", trace_id=trace_id) as track_span:
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
            if isinstance(self.tracker, FallbackTracker):
                tracks = self.tracker.update(det_ins, frame_bgr=self._frame)
            else:
                tracks = self.tracker.update(det_ins)
            track_span.attrs["n_tracks"] = str(len(tracks))

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
                trace_id=trace_id,
            ),
        )

        with self.recorder.span("fusion", trace_id=trace_id) as fus_span:
            facts = tracks_to_facts(
                tracks,
                self._nav,
                calib=self._calib,
                source_id=self.source_id,
                stamp_s=stamp,
            )
            facts = [replace(f, trace_id=trace_id) for f in facts]
            fus_span.attrs["n_facts"] = str(len(facts))

        with self.recorder.span("ontology", trace_id=trace_id):
            for fact in facts:
                self.cache.upsert(fact, now_s=now)
                self.bus.publish(TOPIC_DMI_WORLD_FACT, fact)
                obj = fact_to_world_object(fact)
                changed, stored = self.cache.upsert_object(obj, now_s=now)
                self.bus.publish(TOPIC_DMI_WORLD_OBJECT, stored)
                if changed and stored.first_seen_s == stored.last_seen_s:
                    self.bus.publish(
                        TOPIC_DMI_EVENT,
                        OntologyEvent(
                            event_id=f"ev-{stored.object_id}-{int(now * 1000)}",
                            kind="DETECTED",
                            object_id=stored.object_id,
                            agent_id=self.source_id,
                            detail=stored.type,
                            stamp_s=now,
                            trace_id=trace_id,
                        ),
                    )

        self._maybe_semantic(tracks, stamp_ns=int(stamp * 1e9), trace_id=trace_id)

        with self.recorder.span("scene_analyst", trace_id=trace_id):
            assessment = analyze_scene(facts, stamp_s=stamp, link_ok=self.link_ok)
            self.bus.publish(TOPIC_SCENE, assessment)

    def _maybe_semantic(self, tracks, *, stamp_ns: int, trace_id: str) -> None:
        """Event-driven VE/VL on uncertain tracks — publishes ConceptHit/SceneFact only."""
        if self._semantic is None or self._frame is None:
            return
        from poseidon.router import RouterContext
        from poseidon.ve import apply_concept_hit_attrs

        h, w = self._frame.shape[:2]
        uncertain = [
            t
            for t in tracks
            if float(t.conf) < 0.55
            or (0 <= t.cls_id < len(CERBER_NAMES) and CERBER_NAMES[t.cls_id] in ("obstacle",))
        ]
        if not uncertain:
            return
        t = uncertain[0]
        x1, y1 = max(0, int(t.x1)), max(0, int(t.y1))
        x2, y2 = min(w, int(t.x2)), min(h, int(t.y2))
        if x2 <= x1 or y2 <= y1:
            return
        crop = self._frame[y1:y2, x1:x2]
        if crop.size == 0:
            return
        ctx = RouterContext(
            mission_mode=self.mission_mode,
            has_unknown=True,
            unknown_conf=float(t.conf),
            link_ok=self.link_ok,
        )
        with self.recorder.span("poseidon_ve_vl", trace_id=trace_id) as sp:
            sem = self._semantic.step_roi(
                crop,
                ctx,
                object_id=f"trk-{t.track_id}",
                track_id=int(t.track_id),
                trace_id=trace_id,
                stamp_ns=stamp_ns,
            )
            sp.attrs["n_hits"] = str(len(sem.hits))
            sp.attrs["vl"] = "1" if sem.scene and sem.scene.validity else "0"
        if sem.hits:
            self.bus.publish(
                TOPIC_POSEIDON_VE_HITS,
                ConceptHitArray(hits=sem.hits, stamp_s=time.time(), trace_id=trace_id),
            )
            obj = self.cache.get_object(f"trk-{t.track_id}", now_s=time.time())
            if obj is not None:
                from dataclasses import replace

                merged = replace(
                    obj, attrs=apply_concept_hit_attrs(obj.attrs, sem.hits[0])
                )
                _, stored = self.cache.upsert_object(merged, now_s=time.time())
                self.bus.publish(TOPIC_DMI_WORLD_OBJECT, stored)
        if sem.scene is not None:
            self.bus.publish(TOPIC_POSEIDON_VL_SCENE, sem.scene)

    def ingest_image_poseidon(self, bgr, cerber_dets: list[BusDet]) -> None:
        """Companion path: CV specialists + optional semantic escalate."""
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
            has_unknown=any(c < 0 for c in cls_ids) or any(
                max_conf.get(c, 1.0) < 0.55 for c in cls_ids
            ),
            unknown_conf=min((max_conf.get(c, 0.0) for c in cls_ids), default=0.0),
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
        if self._semantic is not None:
            self._frame = bgr
            # Synthetic track from first low-conf det for VE ROI
            from perception.tracking import Track

            low = [d for d in cerber_dets if d.conf < 0.55]
            if low:
                d0 = low[0]
                name = (
                    CERBER_NAMES[d0.cls_id]
                    if 0 <= d0.cls_id < len(CERBER_NAMES)
                    else "unknown"
                )
                tracks = [
                    Track(
                        track_id=0,
                        cls_id=d0.cls_id,
                        name=name,
                        conf=d0.conf,
                        x1=d0.x1,
                        y1=d0.y1,
                        x2=d0.x2,
                        y2=d0.y2,
                        age=1,
                        hits=1,
                        time_since_update=0,
                    )
                ]
                self._maybe_semantic(
                    tracks, stamp_ns=int(now * 1e9), trace_id=new_trace_id(self.source_id)
                )

    def all_facts(self) -> list[WorldFact]:
        return self.cache.all_facts(now_s=time.time())


def main(bus: SoftBus | None = None) -> SoftBus:
    bus = bus or SoftBus()
    VisionFactsSoftNode(bus)
    return bus


if __name__ == "__main__":
    main()
