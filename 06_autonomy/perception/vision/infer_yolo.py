"""YOLO ONNX detector — preprocess → ORT → decode → NMS."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np

from .decode import Detection, decode_yolo_v8_raw
from .layout import LAYOUT_YOLO_V8_RAW, UnsupportedLayoutError
from .nms import nms
from .preprocess import bgr_to_nchw_float, letterbox
from .session_factory import OrtSession, OrtSessionFactory


@dataclass(frozen=True)
class DetectorConfig:
    model_path: Path
    layout: str
    classes: tuple[str, ...]
    input_h: int
    input_w: int
    confidence: float
    iou: float
    providers: tuple[str, ...]
    input_name: str
    output_name: str
    sha256: str

    @property
    def num_classes(self) -> int:
        return len(self.classes)


class YoloDetector:
    """Flight detector for LAYOUT_YOLO_V8_RAW only."""

    def __init__(
        self,
        cfg: DetectorConfig,
        session: OrtSession,
    ) -> None:
        if cfg.layout != LAYOUT_YOLO_V8_RAW:
            raise UnsupportedLayoutError(
                f"unsupported onnx_layout={cfg.layout!r}; only {LAYOUT_YOLO_V8_RAW!r}"
            )
        if cfg.num_classes < 1:
            raise ValueError("classes list must be non-empty")
        self.cfg = cfg
        self._session = session

    def infer(self, bgr: np.ndarray) -> list[Detection]:
        th, tw = self.cfg.input_h, self.cfg.input_w
        padded, ratio, (pad_x, pad_y) = letterbox(bgr, (th, tw))
        tensor = bgr_to_nchw_float(padded)
        raw = self._session.run(tensor)
        dets = decode_yolo_v8_raw(
            np.asarray(raw),
            num_classes=self.cfg.num_classes,
            conf_thres=self.cfg.confidence,
            ratio=ratio,
            pad_x=pad_x,
            pad_y=pad_y,
            orig_hw=bgr.shape[:2],
        )
        return nms(dets, self.cfg.iou)


def build_detector(
    cfg: DetectorConfig,
    factory: OrtSessionFactory | None = None,
) -> YoloDetector:
    factory = factory or OrtSessionFactory()
    session = factory.create(
        cfg.model_path,
        providers=list(cfg.providers),
        input_name=cfg.input_name,
        output_name=cfg.output_name,
    )
    return YoloDetector(cfg, session)
