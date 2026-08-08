"""Depth / obstacle grid service — FLIGHT-2 stereo or NN depth."""

from __future__ import annotations

import time
from pathlib import Path

from soft_bus.messages import DepthGridMsg, ImageMsg


class DepthService:
    def __init__(self, *, onnx_path: Path | None = None, min_period_s: float = 0.1) -> None:
        self.onnx_path = onnx_path
        self.min_period_s = min_period_s
        self._last_s = 0.0
        self._session = None
        if onnx_path is not None and onnx_path.is_file():
            import onnxruntime as ort

            self._session = ort.InferenceSession(
                str(onnx_path),
                providers=["CUDAExecutionProvider", "CPUExecutionProvider"],
            )

    @property
    def ready(self) -> bool:
        return self._session is not None

    def step(self, image: ImageMsg) -> DepthGridMsg | None:
        now = time.time()
        if now - self._last_s < self.min_period_s:
            return None
        self._last_s = now
        return DepthGridMsg(
            cells=[],
            frame_id="body",
            ok=self._session is not None,
            stamp_s=now,
            stamp_ns=image.stamp_ns,
        )
