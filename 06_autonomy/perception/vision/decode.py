"""Strict YOLO_V8_RAW decode — layout [1, 4+nc, N] only."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .layout import BOX_CHANNELS, LAYOUT_YOLO_V8_RAW, UnsupportedLayoutError


@dataclass(frozen=True)
class Detection:
    cls_id: int
    conf: float
    x1: float
    y1: float
    x2: float
    y2: float


def decode_yolo_v8_raw(
    out: np.ndarray,
    *,
    num_classes: int,
    conf_thres: float,
    ratio: float,
    pad_x: int,
    pad_y: int,
    orig_hw: tuple[int, int],
) -> list[Detection]:
    """Decode Ultralytics raw detect ONNX.

    Contract:
      shape == (1, 4 + num_classes, N)
      channel 0..3 = cx, cy, w, h (letterbox space)
      channel 4.. = class scores
    """
    if num_classes < 1:
        raise ValueError("num_classes must be >= 1")

    arr = np.asarray(out, dtype=np.float32)
    expected_c = BOX_CHANNELS + num_classes

    if arr.ndim != 3 or arr.shape[0] != 1:
        raise UnsupportedLayoutError(
            f"{LAYOUT_YOLO_V8_RAW}: expected rank-3 batch tensor (1, C, N), got shape {arr.shape}"
        )
    if arr.shape[1] != expected_c:
        raise UnsupportedLayoutError(
            f"{LAYOUT_YOLO_V8_RAW}: expected C={expected_c} (4+{num_classes}), "
            f"got C={arr.shape[1]} shape={arr.shape}"
        )

    pred = arr[0]  # [C, N]
    boxes = pred[:BOX_CHANNELS, :]
    scores = pred[BOX_CHANNELS:, :]
    cls_ids = np.argmax(scores, axis=0)
    confs = scores[cls_ids, np.arange(scores.shape[1])]

    oh, ow = orig_hw
    dets: list[Detection] = []
    for i in range(pred.shape[1]):
        conf = float(confs[i])
        if conf < conf_thres:
            continue
        cx, cy, w, h = (float(boxes[0, i]), float(boxes[1, i]), float(boxes[2, i]), float(boxes[3, i]))
        x1 = (cx - w / 2.0 - pad_x) / ratio
        y1 = (cy - h / 2.0 - pad_y) / ratio
        x2 = (cx + w / 2.0 - pad_x) / ratio
        y2 = (cy + h / 2.0 - pad_y) / ratio
        dets.append(
            Detection(
                cls_id=int(cls_ids[i]),
                conf=conf,
                x1=float(np.clip(x1, 0, ow - 1)),
                y1=float(np.clip(y1, 0, oh - 1)),
                x2=float(np.clip(x2, 0, ow - 1)),
                y2=float(np.clip(y2, 0, oh - 1)),
            )
        )
    return dets
