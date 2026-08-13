"""Draw CERBER detections / tracks on BGR frames."""

from __future__ import annotations

import cv2
import numpy as np

from .ipc import Detection, TrackRow, VisionHealth


def draw_boxes(
    bgr: np.ndarray,
    detections: list[Detection],
) -> np.ndarray:
    frame = bgr.copy()
    for d in detections:
        x1, y1, x2, y2 = int(d.x1), int(d.y1), int(d.x2), int(d.y2)
        cv2.rectangle(frame, (x1, y1), (x2, y2), (220, 220, 220), 1)
        if d.track_id >= 0:
            cv2.putText(
                frame,
                f"{d.track_id:02d}",
                (x1, max(14, y1 - 4)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.45,
                (240, 240, 240),
                1,
                cv2.LINE_AA,
            )
    return frame


def draw_overlay(
    bgr: np.ndarray,
    detections: list[Detection],
    tracks: list[TrackRow],
    health: VisionHealth,
    mode: str,
) -> np.ndarray:
    frame = bgr.copy()
    for d in detections:
        x1, y1, x2, y2 = int(d.x1), int(d.y1), int(d.x2), int(d.y2)
        label = d.name or str(d.cls_id)
        if d.track_id >= 0:
            label = f"id{d.track_id} {label}"
        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 220, 80), 2)
        cv2.putText(
            frame,
            f"{label} {d.conf:.2f}",
            (x1, max(16, y1 - 6)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (0, 220, 80),
            1,
            cv2.LINE_AA,
        )
    for t in tracks:
        cv2.putText(
            frame,
            f"T{t.track_id}:{t.name}",
            (int(t.x1), int(t.y2) + 14),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.45,
            (80, 200, 255),
            1,
            cv2.LINE_AA,
        )
    status = "OK" if health.vision_ok else "BLOCKED"
    hud = (
        f"CERBER {status} · {health.detail[:48]} · "
        f"det={len(detections)} trk={len(tracks)} · {mode} · "
        f"{health.infer_fps:.1f} FPS"
    )
    cv2.putText(
        frame,
        hud,
        (8, 22),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55,
        (40, 40, 255) if not health.vision_ok else (40, 220, 40),
        2,
        cv2.LINE_AA,
    )
    return frame
