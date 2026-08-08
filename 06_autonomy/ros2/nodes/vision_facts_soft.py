"""Vision → Track → Fusion → WorldFact + SceneAssessment (+ optional POSEIDON).

No-link: still publishes local facts/scene; GSC optional (ADR-002/004).
"""

from __future__ import annotations

import time
from pathlib import Path

from dmi.messages import TOPIC_DMI_WORLD_FACT, WorldFact
from dmi.world_cache import SharedWorldCache
from perception.fusion.scene_analyst import analyze_scene
from perception.fusion.scene_fusion import CERBER_NAMES, FusionCalib, tracks_to_facts
from perception.tracking import DetIn, FallbackTracker, IouTracker
from soft_bus.bus import SoftBus
from soft_bus.messages import (
    TOPIC_CAM_FORWARD,
    TOPIC_DETECTIONS,
    TOPIC_NAV,
    TOPIC_NAV_FUSED,
    TOPIC_POSEIDON_ACTIVE,
    TOPIC_POSEIDON_DETECTIONS,
    TOPIC_SCENE,
    TOPIC_TRACKS,
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
    ) -> None:
        self.bus = bus
        self.source_id = source_id
        self.mission_mode = mission_mode
        self.link_ok = link_ok
        self.prefer_fused_nav = prefer_fused_nav
        self.tracker = FallbackTracker() if use_botsort else IouTracker()
        self.cache = SharedWorldCache()
        self._nav: NavStateMsg | None = None
        self._frame: object | None = None
        self._calib = _load_fusion_calib()
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
        dets = list(arr.detections)

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
        if isinstance(self.tracker, FallbackTracker):
            tracks = self.tracker.update(det_ins, frame_bgr=self._frame)
        else:
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
            tracks,
            self._nav,
            calib=self._calib,
            source_id=self.source_id,
            stamp_s=stamp,
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
