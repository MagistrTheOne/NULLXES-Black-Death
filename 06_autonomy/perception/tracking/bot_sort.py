"""BoT-SORT-style tracker with optional CMC + IOU degraded fallback.

Primary path: constant-velocity KF on bbox center/size + IOU association.
CMC: ECC affine warp of previous boxes when prev/curr gray frames provided.
ReID: off (budget).
"""

from __future__ import annotations

from dataclasses import dataclass

from .iou_tracker import DetIn, IouTracker, Track, _iou


@dataclass
class _KFTrack:
    track_id: int
    cls_id: int
    name: str
    conf: float
    x1: float
    y1: float
    x2: float
    y2: float
    vx: float = 0.0
    vy: float = 0.0
    age: int = 0
    hits: int = 0
    time_since_update: int = 0


def _cmc_warp_box(
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    affine: object | None,
) -> tuple[float, float, float, float]:
    if affine is None:
        return x1, y1, x2, y2
    import numpy as np

    A = np.asarray(affine, dtype=float)
    pts = np.array([[x1, y1, 1.0], [x2, y2, 1.0]], dtype=float).T
    # 2x3 affine
    out = A @ pts
    return float(out[0, 0]), float(out[1, 0]), float(out[0, 1]), float(out[1, 1])


def estimate_cmc(prev_gray: object, curr_gray: object) -> object | None:
    """Return 2x3 affine (prev→curr) or None."""
    try:
        import cv2
        import numpy as np

        warp = np.eye(2, 3, dtype=np.float32)
        criteria = (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 50, 1e-3)
        ok, warp = cv2.findTransformECC(
            prev_gray, curr_gray, warp, cv2.MOTION_EUCLIDEAN, criteria, None, 1
        )
        return warp if ok else None
    except Exception:
        return None


class BotSortTracker:
    def __init__(
        self,
        *,
        iou_thresh: float = 0.3,
        max_age: int = 30,
        min_hits: int = 1,
        use_cmc: bool = True,
    ) -> None:
        self.iou_thresh = iou_thresh
        self.max_age = max_age
        self.min_hits = min_hits
        self.use_cmc = use_cmc
        self._next_id = 1
        self._tracks: list[_KFTrack] = []
        self._prev_gray = None

    def update(
        self,
        detections: list[DetIn],
        *,
        frame_bgr: object | None = None,
    ) -> list[Track]:
        affine = None
        gray = None
        if frame_bgr is not None and self.use_cmc:
            import cv2

            gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
            if self._prev_gray is not None:
                affine = estimate_cmc(self._prev_gray, gray)
            self._prev_gray = gray

        for t in self._tracks:
            # CMC compensate then constant-velocity predict
            x1, y1, x2, y2 = _cmc_warp_box(t.x1, t.y1, t.x2, t.y2, affine)
            t.x1, t.y1, t.x2, t.y2 = x1 + t.vx, y1 + t.vy, x2 + t.vx, y2 + t.vy
            t.time_since_update += 1
            t.age += 1

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
            cx0 = 0.5 * (t.x1 + t.x2)
            cy0 = 0.5 * (t.y1 + t.y2)
            cx1 = 0.5 * (d.x1 + d.x2)
            cy1 = 0.5 * (d.y1 + d.y2)
            t.vx = cx1 - cx0
            t.vy = cy1 - cy0
            t.x1, t.y1, t.x2, t.y2 = d.x1, d.y1, d.x2, d.y2
            t.conf = d.conf
            t.name = d.name
            t.hits += 1
            t.time_since_update = 0

        for di, d in enumerate(detections):
            if di in matched_d:
                continue
            self._tracks.append(
                _KFTrack(
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

        self._tracks = [t for t in self._tracks if t.time_since_update <= self.max_age]
        out: list[Track] = []
        for t in self._tracks:
            if t.time_since_update == 0 and t.hits >= self.min_hits:
                out.append(
                    Track(
                        track_id=t.track_id,
                        cls_id=t.cls_id,
                        name=t.name,
                        conf=t.conf,
                        x1=t.x1,
                        y1=t.y1,
                        x2=t.x2,
                        y2=t.y2,
                        age=t.age,
                        hits=t.hits,
                        time_since_update=t.time_since_update,
                    )
                )
        return out


class FallbackTracker:
    """BoT-SORT primary; on failure/overbudget → IOU tracker."""

    def __init__(
        self,
        *,
        budget_ms: float = 8.0,
        use_cmc: bool = True,
    ) -> None:
        self.budget_ms = budget_ms
        self.primary = BotSortTracker(use_cmc=use_cmc)
        self.fallback = IouTracker()
        self.mode = "botsort"
        self.last_latency_ms = 0.0

    def update(
        self,
        detections: list[DetIn],
        *,
        frame_bgr: object | None = None,
        force_iou: bool = False,
    ) -> list[Track]:
        import time

        if force_iou or self.mode == "iou":
            self.mode = "iou"
            t0 = time.perf_counter()
            out = self.fallback.update(detections)
            self.last_latency_ms = (time.perf_counter() - t0) * 1000.0
            return out
        t0 = time.perf_counter()
        try:
            out = self.primary.update(detections, frame_bgr=frame_bgr)
        except Exception:
            self.mode = "iou"
            out = self.fallback.update(detections)
            self.last_latency_ms = (time.perf_counter() - t0) * 1000.0
            return out
        self.last_latency_ms = (time.perf_counter() - t0) * 1000.0
        if self.last_latency_ms > self.budget_ms:
            self.mode = "iou"
            return self.fallback.update(detections)
        self.mode = "botsort"
        return out
