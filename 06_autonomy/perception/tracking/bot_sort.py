"""BoT-SORT-style tracker: Kalman (cx,cy,a,h) + ECC CMC + Byte two-stage.

ReID off (budget). Overrun: keep this frame's primary output; next frame uses IOU.
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
    x: float  # cx
    y: float  # cy
    a: float  # aspect w/h
    h: float
    vx: float = 0.0
    vy: float = 0.0
    va: float = 0.0
    vh: float = 0.0
    age: int = 0
    hits: int = 0
    time_since_update: int = 0

    def box(self) -> tuple[float, float, float, float]:
        w = max(1.0, self.a * self.h)
        h = max(1.0, self.h)
        return self.x - w * 0.5, self.y - h * 0.5, self.x + w * 0.5, self.y + h * 0.5


def _det_xyah(d: DetIn) -> tuple[float, float, float, float]:
    w = max(1.0, d.x2 - d.x1)
    h = max(1.0, d.y2 - d.y1)
    return 0.5 * (d.x1 + d.x2), 0.5 * (d.y1 + d.y2), w / h, h


def _cmc_warp_xyah(
    x: float,
    y: float,
    a: float,
    h: float,
    affine: object | None,
) -> tuple[float, float, float, float]:
    if affine is None:
        return x, y, a, h
    import numpy as np

    A = np.asarray(affine, dtype=float)
    w = max(1.0, a * h)
    x1, y1 = x - w * 0.5, y - h * 0.5
    x2, y2 = x + w * 0.5, y + h * 0.5
    pts = np.array([[x1, y1, 1.0], [x2, y2, 1.0]], dtype=float).T
    out = A @ pts
    nx1, ny1, nx2, ny2 = float(out[0, 0]), float(out[1, 0]), float(out[0, 1]), float(out[1, 1])
    nw = max(1.0, nx2 - nx1)
    nh = max(1.0, ny2 - ny1)
    return 0.5 * (nx1 + nx2), 0.5 * (ny1 + ny2), nw / nh, nh


def estimate_cmc(prev_gray: object, curr_gray: object) -> object | None:
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
        low_iou_thresh: float = 0.15,
        high_conf: float = 0.5,
        max_age: int = 30,
        min_hits: int = 1,
        use_cmc: bool = True,
    ) -> None:
        self.iou_thresh = iou_thresh
        self.low_iou_thresh = low_iou_thresh
        self.high_conf = high_conf
        self.max_age = max_age
        self.min_hits = min_hits
        self.use_cmc = use_cmc
        self._next_id = 1
        self._tracks: list[_KFTrack] = []
        self._prev_gray = None

    def _predict(self, affine: object | None) -> None:
        for t in self._tracks:
            x, y, a, h = _cmc_warp_xyah(t.x, t.y, t.a, t.h, affine)
            t.x, t.y, t.a, t.h = x + t.vx, y + t.vy, a + t.va, h + t.vh
            t.time_since_update += 1
            t.age += 1

    def _associate(
        self,
        tracks: list[_KFTrack],
        dets: list[DetIn],
        thresh: float,
    ) -> tuple[list[tuple[int, int]], set[int], set[int]]:
        pairs: list[tuple[float, int, int]] = []
        for ti, t in enumerate(tracks):
            bx = t.box()
            tb = DetIn(t.cls_id, t.name, t.conf, *bx)
            for di, d in enumerate(dets):
                if t.cls_id != d.cls_id:
                    continue
                score = _iou(tb, d)
                if score >= thresh:
                    pairs.append((score, ti, di))
        pairs.sort(reverse=True)
        matched_t: set[int] = set()
        matched_d: set[int] = set()
        matches: list[tuple[int, int]] = []
        for _, ti, di in pairs:
            if ti in matched_t or di in matched_d:
                continue
            matched_t.add(ti)
            matched_d.add(di)
            matches.append((ti, di))
        return matches, matched_t, matched_d

    def _update_track(self, t: _KFTrack, d: DetIn) -> None:
        cx, cy, a, h = _det_xyah(d)
        t.vx = cx - t.x
        t.vy = cy - t.y
        t.va = a - t.a
        t.vh = h - t.h
        t.x, t.y, t.a, t.h = cx, cy, a, h
        t.conf = d.conf
        t.name = d.name
        t.hits += 1
        t.time_since_update = 0

    def update(
        self,
        detections: list[DetIn],
        *,
        frame_bgr: object | None = None,
    ) -> list[Track]:
        affine = None
        if frame_bgr is not None and self.use_cmc:
            import cv2

            gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
            if self._prev_gray is not None:
                affine = estimate_cmc(self._prev_gray, gray)
            self._prev_gray = gray

        self._predict(affine)

        high = [d for d in detections if d.conf >= self.high_conf]
        low = [d for d in detections if d.conf < self.high_conf]
        matches, mt, md = self._associate(self._tracks, high, self.iou_thresh)
        for ti, di in matches:
            self._update_track(self._tracks[ti], high[di])

        unmatched_tracks = [self._tracks[i] for i in range(len(self._tracks)) if i not in mt]
        matches2, _mt2, md2 = self._associate(unmatched_tracks, low, self.low_iou_thresh)
        for ti, di in matches2:
            self._update_track(unmatched_tracks[ti], low[di])

        unmatched_high = [d for i, d in enumerate(high) if i not in md]
        for d in unmatched_high:
            cx, cy, a, h = _det_xyah(d)
            self._tracks.append(
                _KFTrack(
                    track_id=self._next_id,
                    cls_id=d.cls_id,
                    name=d.name,
                    conf=d.conf,
                    x=cx,
                    y=cy,
                    a=a,
                    h=h,
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
                x1, y1, x2, y2 = t.box()
                out.append(
                    Track(
                        track_id=t.track_id,
                        cls_id=t.cls_id,
                        name=t.name,
                        conf=t.conf,
                        x1=x1,
                        y1=y1,
                        x2=x2,
                        y2=y2,
                        age=t.age,
                        hits=t.hits,
                        time_since_update=t.time_since_update,
                    )
                )
        return out


class FallbackTracker:
    """BoT-SORT primary; on failure/overbudget switch to IOU on the *next* frame."""

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
            self.last_latency_ms = (time.perf_counter() - t0) * 1000.0
            return self.fallback.update(detections)
        self.last_latency_ms = (time.perf_counter() - t0) * 1000.0
        if self.last_latency_ms > self.budget_ms:
            self.mode = "iou"
        else:
            self.mode = "botsort"
        return out
