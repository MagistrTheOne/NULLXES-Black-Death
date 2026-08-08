"""Depth SoftBus node — FLIGHT-2 obstacle grid."""

from __future__ import annotations

from pathlib import Path

from perception.depth.depth_service import DepthService
from soft_bus.bus import SoftBus
from soft_bus.messages import TOPIC_CAM_FORWARD, TOPIC_DEPTH_GRID, ImageMsg


class DepthSoftNode:
    def __init__(self, bus: SoftBus, *, onnx_path: Path | None = None) -> None:
        self.bus = bus
        self.svc = DepthService(onnx_path=onnx_path)
        bus.subscribe(TOPIC_CAM_FORWARD, self._on_cam)

    def _on_cam(self, img: ImageMsg) -> None:
        grid = self.svc.step(img)
        if grid is not None:
            self.bus.publish(TOPIC_DEPTH_GRID, grid)


def main(bus: SoftBus | None = None) -> SoftBus:
    bus = bus or SoftBus()
    DepthSoftNode(bus)
    return bus


if __name__ == "__main__":
    main()
