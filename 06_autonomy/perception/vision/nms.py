"""Class-aware NMS for Detection lists."""

from __future__ import annotations

from .decode import Detection


def nms(detections: list[Detection], iou_thres: float) -> list[Detection]:
    if not detections:
        return []
    if not (0.0 < iou_thres <= 1.0):
        raise ValueError(f"iou_thres must be in (0, 1], got {iou_thres}")

    by_cls: dict[int, list[Detection]] = {}
    for d in detections:
        by_cls.setdefault(d.cls_id, []).append(d)

    kept: list[Detection] = []
    for group in by_cls.values():
        kept.extend(_nms_one_class(group, iou_thres))
    kept.sort(key=lambda d: d.conf, reverse=True)
    return kept


def _nms_one_class(dets: list[Detection], iou_thres: float) -> list[Detection]:
    order = sorted(range(len(dets)), key=lambda i: dets[i].conf, reverse=True)
    suppressed = [False] * len(dets)
    out: list[Detection] = []
    for oi, i in enumerate(order):
        if suppressed[i]:
            continue
        out.append(dets[i])
        for j in order[oi + 1 :]:
            if suppressed[j]:
                continue
            if _iou(dets[i], dets[j]) > iou_thres:
                suppressed[j] = True
    return out


def _iou(a: Detection, b: Detection) -> float:
    x1 = max(a.x1, b.x1)
    y1 = max(a.y1, b.y1)
    x2 = min(a.x2, b.x2)
    y2 = min(a.y2, b.y2)
    inter = max(0.0, x2 - x1) * max(0.0, y2 - y1)
    if inter <= 0.0:
        return 0.0
    area_a = max(0.0, a.x2 - a.x1) * max(0.0, a.y2 - a.y1)
    area_b = max(0.0, b.x2 - b.x1) * max(0.0, b.y2 - b.y1)
    union = area_a + area_b - inter
    if union <= 0.0:
        return 0.0
    return float(inter / union)
