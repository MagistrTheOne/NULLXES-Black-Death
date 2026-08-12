"""Rate-limited SegFormer-B0 SoftBus service — real ORT or fail-closed."""

from __future__ import annotations

import time
from pathlib import Path

import numpy as np

from soft_bus.messages import ImageMsg, SegMetaMsg

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
        min_period_s: float = 0.12,
        session: object | None = None,
        input_size: int = 512,
        min_pixels: int = 64,
        input_name: str = "input",
    ) -> None:
        self.onnx_path = onnx_path
        self.min_period_s = min_period_s
        self.input_size = int(input_size)
        self.min_pixels = int(min_pixels)
        self.input_name = input_name
        self._last_s = 0.0
        self._session = session
        if self._session is None and onnx_path is not None and onnx_path.is_file():
            import onnxruntime as ort

            available = set(ort.get_available_providers())
            providers = [p for p in ("CUDAExecutionProvider", "CPUExecutionProvider") if p in available]
            if not providers:
                providers = ["CPUExecutionProvider"]
            self._session = ort.InferenceSession(str(onnx_path), providers=providers)
            ins = self._session.get_inputs()
            if ins:
                self.input_name = ins[0].name

    @property
    def ready(self) -> bool:
        return self._session is not None

    def step(self, image: ImageMsg) -> SegMetaMsg | None:
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
        try:
            present = self._infer_classes(image.bgr)
        except Exception:
            return SegMetaMsg(
                classes_present=[],
                latency_ms=(time.perf_counter() - t0) * 1000.0,
                ok=False,
                stamp_s=now,
                stamp_ns=image.stamp_ns,
            )
        return SegMetaMsg(
            classes_present=present,
            latency_ms=(time.perf_counter() - t0) * 1000.0,
            ok=True,
            stamp_s=now,
            stamp_ns=image.stamp_ns,
        )

    def _infer_classes(self, bgr: object) -> list[str]:
        arr = np.asarray(bgr)
        if arr.ndim != 3 or arr.shape[2] < 3:
            raise ValueError("bgr must be HWC")
        import cv2

        rgb = arr[:, :, :3][:, :, ::-1]
        resized = cv2.resize(rgb, (self.input_size, self.input_size), interpolation=cv2.INTER_LINEAR)
        tensor = np.transpose(resized.astype(np.float32) / 255.0, (2, 0, 1))[None, ...]
        raw = self._session.run(None, {self.input_name: tensor})[0]
        logits = np.asarray(raw)
        if logits.ndim == 4:
            # [1, C, H, W] or [1, H, W, C]
            if logits.shape[1] == len(SEG_CLASSES) or logits.shape[1] > 4:
                labels = np.argmax(logits[0], axis=0)
            else:
                labels = np.argmax(logits[0], axis=-1)
        elif logits.ndim == 3:
            labels = np.argmax(logits, axis=0) if logits.shape[0] == len(SEG_CLASSES) else np.argmax(logits, axis=-1)
        elif logits.ndim == 2:
            labels = logits.astype(np.int64)
        else:
            raise ValueError(f"unsupported seg output ndim={logits.ndim}")
        present: list[str] = []
        for idx, name in enumerate(SEG_CLASSES):
            if int(np.sum(labels == idx)) >= self.min_pixels:
                present.append(name)
        return present
