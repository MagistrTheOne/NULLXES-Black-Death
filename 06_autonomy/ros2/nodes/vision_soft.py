"""Vision node on SoftBus — requires real ONNX weights."""

from __future__ import annotations

import time
from pathlib import Path

from soft_bus.bus import SoftBus
from soft_bus.messages import (
    TOPIC_CAM_FORWARD,
    TOPIC_DETECTIONS,
    TOPIC_VISION_HEALTH,
    Detection as BusDet,
    DetectionArray,
    ImageMsg,
    VisionHealth,
)


class BlockedError(RuntimeError):
    """Hardware or artifact required — do not invent substitutes."""


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


class VisionSoftNode:
    def __init__(self, bus: SoftBus, cfg_path: Path | None = None) -> None:
        from perception.vision.vision_node import BlockedError as PipelineBlocked
        from perception.vision.vision_node import VisionPipeline

        path = cfg_path or (
            _repo_root() / "06_autonomy" / "models" / "configs" / "detector_alpha.yaml"
        )
        try:
            self.pipeline = VisionPipeline(path)
        except PipelineBlocked as exc:
            raise BlockedError(str(exc)) from exc
        self.bus = bus
        bus.subscribe(TOPIC_CAM_FORWARD, self._on_image)

    def _on_image(self, msg: ImageMsg) -> None:
        now = time.time()
        try:
            dets = self.pipeline.process_bgr(msg.bgr)
            self.bus.publish(
                TOPIC_DETECTIONS,
                DetectionArray(
                    detections=[BusDet(d.cls_id, d.conf, d.x1, d.y1, d.x2, d.y2) for d in dets],
                    camera=msg.camera,
                    stamp_s=now,
                ),
            )
            self.bus.publish(TOPIC_VISION_HEALTH, VisionHealth(True, 1, "", now))
        except Exception as exc:  # noqa: BLE001
            self.bus.publish(
                TOPIC_VISION_HEALTH,
                VisionHealth(False, 0, str(exc), now),
            )


def main(bus: SoftBus | None = None) -> SoftBus:
    bus = bus or SoftBus()
    VisionSoftNode(bus)
    return bus


if __name__ == "__main__":
    main()
