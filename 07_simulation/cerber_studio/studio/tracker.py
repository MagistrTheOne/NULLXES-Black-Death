"""IOU multi-object tracker with stable IDs — Studio tracker v1."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Track:
    track_id: int
    cls_id: int
    name: str
    conf: float
    x1: float
    y1: float
    x2: float
    y2: float
    age: int
    hits: int
    time_since_update: int


@dataclass
class DetIn:
    cls_id: int
    name: str
    conf: float
    x1: float
    y1: float
    x2: float
    y2: float


def _iou(a: DetIn | Track, b: DetIn | Track) -> float:
    ax1, ay1, ax2, ay2 = a.x1, a.y1, a.x2, a.y2
    bx1, by1, bx2, by2 = b.x1, b.y1, b.x2, b.y2
    ix1, iy1 = max(ax1, bx1), max(ay1, by1)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    iw, ih = max(0.0, ix2 - ix1), max(0.0, iy2 - iy1)
    inter = iw * ih
    if inter <= 0.0:
        return 0.0
    area_a = max(0.0, ax2 - ax1) * max(0.0, ay2 - ay1)
    area_b = max(0.0, bx2 - bx1) * max(0.0, by2 - by1)
    union = area_a + area_b - inter
    return inter / union if union > 0.0 else 0.0


class IouTracker:
    """Greedy IOU association + stable integer IDs."""

    def __init__(self, iou_thresh: float = 0.3, max_age: int = 30, min_hits: int = 1) -> None:
        self.iou_thresh = iou_thresh
        self.max_age = max_age
        self.min_hits = min_hits
        self._next_id = 1
        self._tracks: list[Track] = []

    def update(self, detections: list[DetIn]) -> list[Track]:
        for t in self._tracks:
            t.time_since_update += 1
            t.age += 1

        unmatched_dets = set(range(len(detections)))
        unmatched_trks = set(range(len(self._tracks)))
        pairs: list[tuple[float, int, int]] = []
        for ti, t in enumerate(self._tracks):
            for di, d in enumerate(detections):
                if t.cls_id != d.cls_id:
                    continue
                score = _iou(t, d)
                if score >= self.iou_thresh:
                    pairs.append((score, ti, di))
        pairs.sort(reverse=True)

        matched_t: set[int] = set()
        matched_d: set[int] = set()
        for _, ti, di in pairs:
            if ti in matched_t or di in matched_d:
                continue
            matched_t.add(ti)
            matched_d.add(di)
            d = detections[di]
            t = self._tracks[ti]
            t.x1, t.y1, t.x2, t.y2 = d.x1, d.y1, d.x2, d.y2
            t.conf = d.conf
            t.name = d.name
            t.hits += 1
            t.time_since_update = 0

        unmatched_trks -= matched_t
        unmatched_dets -= matched_d

        for di in unmatched_dets:
            d = detections[di]
            self._tracks.append(
                Track(
                    track_id=self._next_id,
                    cls_id=d.cls_id,
                    name=d.name,
                    conf=d.conf,
                    x1=d.x1,
                    y1=d.y1,
                    x2=d.x2,
                    y2=d.y2,
                    age=1,
                    hits=1,
                    time_since_update=0,
                )
            )
            self._next_id += 1

        alive: list[Track] = []
        for t in self._tracks:
            if t.time_since_update > self.max_age:
                continue
            alive.append(t)
        self._tracks = alive

        return [
            t
            for t in self._tracks
            if t.time_since_update == 0 and t.hits >= self.min_hits
        ]
