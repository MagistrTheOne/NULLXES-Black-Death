"""Segmentation SoftBus node — rate-limited SegFormer service."""

from __future__ import annotations

from pathlib import Path

from perception.segmentation.segformer_service import SegFormerService
from soft_bus.bus import SoftBus
from soft_bus.messages import TOPIC_CAM_FORWARD, TOPIC_VISION_SEG, ImageMsg


class SegSoftNode:
    def __init__(self, bus: SoftBus, *, onnx_path: Path | None = None) -> None:
        self.bus = bus
        self.svc = SegFormerService(onnx_path=onnx_path)
        bus.subscribe(TOPIC_CAM_FORWARD, self._on_cam)

    def _on_cam(self, img: ImageMsg) -> None:
        meta = self.svc.step(img)
        if meta is not None:
            self.bus.publish(TOPIC_VISION_SEG, meta)


def main(bus: SoftBus | None = None) -> SoftBus:
    bus = bus or SoftBus()
    SegSoftNode(bus)
    return bus


if __name__ == "__main__":
    main()
