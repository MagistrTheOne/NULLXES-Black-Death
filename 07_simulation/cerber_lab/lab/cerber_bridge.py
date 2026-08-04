"""Optional real CERBER ONNX on sim frames — no fake detections."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

REPO = Path(__file__).resolve().parents[3]
AUTONOMY = REPO / "06_autonomy"
if str(AUTONOMY) not in sys.path:
    sys.path.insert(0, str(AUTONOMY))


@dataclass
class CerberStatus:
    ok: bool
    detail: str
    names: list[str]


@dataclass
class Box:
    name: str
    conf: float
    x1: int
    y1: int
    x2: int
    y2: int


class CerberBridge:
    def __init__(self, config_name: str = "detector_alpha_v2.yaml") -> None:
        self.enabled = False
        self.status = CerberStatus(False, "not loaded", [])
        self._pipe = None
        self.config_name = config_name

    def try_load(self) -> CerberStatus:
        cfg = REPO / "06_autonomy" / "models" / "configs" / self.config_name
        if not cfg.is_file():
            # fallback chain
            for name in (
                self.config_name,
                "detector_alpha_v2b.yaml",
                "detector_alpha_v2.yaml",
                "detector_alpha.yaml",
            ):
                cand = REPO / "06_autonomy" / "models" / "configs" / name
                if cand.is_file():
                    cfg = cand
                    break
        try:
            from perception.vision.vision_node import VisionPipeline

            self._pipe = VisionPipeline(cfg)
            self.status = CerberStatus(True, f"loaded {cfg.name}", list(self._pipe.names))
            self.enabled = True
        except Exception as exc:  # noqa: BLE001
            self._pipe = None
            self.enabled = False
            self.status = CerberStatus(False, f"BLOCKED: {exc}", [])
        return self.status

    def infer(self, bgr: np.ndarray) -> list[Box]:
        if not self.enabled or self._pipe is None:
            return []
        dets = self._pipe.process_bgr(bgr)
        names = self._pipe.names
        out: list[Box] = []
        for d in dets:
            name = names[d.cls_id] if 0 <= d.cls_id < len(names) else str(d.cls_id)
            out.append(
                Box(
                    name=name,
                    conf=float(d.conf),
                    x1=int(d.x1),
                    y1=int(d.y1),
                    x2=int(d.x2),
                    y2=int(d.y2),
                )
            )
        return out

    @staticmethod
    def draw(bgr: np.ndarray, boxes: list[Box], hud: str) -> np.ndarray:
        frame = bgr.copy()
        for b in boxes:
            cv2.rectangle(frame, (b.x1, b.y1), (b.x2, b.y2), (0, 220, 80), 2)
            cv2.putText(
                frame,
                f"{b.name} {b.conf:.2f}",
                (b.x1, max(16, b.y1 - 6)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (0, 220, 80),
                1,
                cv2.LINE_AA,
            )
        cv2.putText(
            frame,
            hud,
            (8, 22),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (40, 40, 255),
            2,
            cv2.LINE_AA,
        )
        return frame
