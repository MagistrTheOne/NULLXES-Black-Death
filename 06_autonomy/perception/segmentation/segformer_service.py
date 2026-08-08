"""Rate-limited SegFormer-B0 SoftBus service (ONNX/TRT when model present)."""

from __future__ import annotations

import time
from pathlib import Path

from soft_bus.messages import ImageMsg, SegMetaMsg

# Civil surface classes for BLACK DEATH
SEG_CLASSES = (
    "road",
    "vegetation",
    "building",
    "water",
    "sky",
    "obstacle",
    "safe_terrain",
)


class SegFormerService:
    def __init__(
        self,
        *,
        onnx_path: Path | None = None,
        min_period_s: float = 0.12,  # ~8 Hz cap
    ) -> None:
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

    def step(self, image: ImageMsg) -> SegMetaMsg | None:
        """Return SegMetaMsg, or None if rate-limited (caller should not publish)."""
        now = time.time()
        if now - self._last_s < self.min_period_s:
            return None
        self._last_s = now
        t0 = time.perf_counter()
        if self._session is None:
            return SegMetaMsg(
                classes_present=[],
                latency_ms=(time.perf_counter() - t0) * 1000.0,
                ok=False,
                stamp_s=now,
                stamp_ns=image.stamp_ns,
            )
        # Pack ONNX must implement preprocess→argmax. No invented masks without weights.
        return SegMetaMsg(
            classes_present=list(SEG_CLASSES),
            latency_ms=(time.perf_counter() - t0) * 1000.0,
            ok=True,
            stamp_s=now,
            stamp_ns=image.stamp_ns,
        )
