#!/usr/bin/env python3
"""CERBER Studio worker process — ORT detect + IOU tracker over ZMQ."""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]  # cerber_studio/
REPO = ROOT.parents[1]  # repo root (07_simulation/..)
AUTONOMY = REPO / "06_autonomy"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(AUTONOMY))

from studio.ipc import (  # noqa: E402
    DEFAULT_FRAME_ENDPOINT,
    DEFAULT_RESULT_ENDPOINT,
    Detection,
    FrameSubscriber,
    ResultPublisher,
    TrackRow,
    VisionHealth,
    WorkerResult,
)
from studio.tracker import DetIn, IouTracker  # noqa: E402


def load_pipeline(config_name: str):
    from perception.vision.vision_node import VisionPipeline

    cfg = REPO / "06_autonomy" / "models" / "configs" / config_name
    return VisionPipeline(cfg)


def main() -> int:
    ap = argparse.ArgumentParser(description="CERBER Studio worker")
    ap.add_argument("--config", default="detector_alpha_v2.yaml")
    ap.add_argument("--frames", default=DEFAULT_FRAME_ENDPOINT)
    ap.add_argument("--results", default=DEFAULT_RESULT_ENDPOINT)
    args = ap.parse_args()

    pub = ResultPublisher(args.results)
    sub = FrameSubscriber(args.frames)
    tracker = IouTracker()
    pipe = None
    names: list[str] = []
    detail = "starting"
    vision_ok = False

    try:
        pipe = load_pipeline(args.config)
        names = list(pipe.names)
        vision_ok = True
        detail = f"loaded {args.config}"
    except Exception as exc:  # noqa: BLE001
        pipe = None
        vision_ok = False
        detail = f"BLOCKED: {exc}"

    # announce health so UI sees worker alive
    pub.send(
        WorkerResult(
            stamp_s=time.time(),
            health=VisionHealth(
                vision_ok=vision_ok,
                cams_alive=1 if vision_ok else 0,
                detail=detail,
                stamp_s=time.time(),
                infer_fps=0.0,
            ),
        )
    )

    t_window = time.perf_counter()
    n_infer = 0
    infer_fps = 0.0

    while True:
        got = sub.recv()
        if got is None:
            continue
        bgr, _meta = got
        stamp = time.time()
        dets_out: list[Detection] = []
        tracks_out: list[TrackRow] = []
        jpeg = b""

        if pipe is None or not vision_ok:
            health = VisionHealth(
                vision_ok=False,
                cams_alive=0,
                detail=detail,
                stamp_s=stamp,
                infer_fps=0.0,
            )
            # still echo frame for PiP without boxes
            ok, buf = cv2.imencode(".jpg", bgr, [int(cv2.IMWRITE_JPEG_QUALITY), 75])
            jpeg = buf.tobytes() if ok else b""
            pub.send(
                WorkerResult(
                    stamp_s=stamp,
                    health=health,
                    detections=[],
                    tracks=[],
                    jpeg=jpeg,
                )
            )
            continue

        t0 = time.perf_counter()
        try:
            raw = pipe.process_bgr(bgr)
        except Exception as exc:  # noqa: BLE001
            vision_ok = False
            detail = f"BLOCKED infer: {exc}"
            pub.send(
                WorkerResult(
                    stamp_s=stamp,
                    health=VisionHealth(False, 0, detail, stamp, 0.0),
                )
            )
            continue

        det_ins: list[DetIn] = []
        for d in raw:
            name = names[d.cls_id] if 0 <= d.cls_id < len(names) else str(d.cls_id)
            det_ins.append(
                DetIn(
                    cls_id=int(d.cls_id),
                    name=name,
                    conf=float(d.conf),
                    x1=float(d.x1),
                    y1=float(d.y1),
                    x2=float(d.x2),
                    y2=float(d.y2),
                )
            )
        tracks = tracker.update(det_ins)
        id_by_box: dict[tuple[int, int, int, int], int] = {}
        for t in tracks:
            key = (int(t.x1), int(t.y1), int(t.x2), int(t.y2))
            id_by_box[key] = t.track_id
            tracks_out.append(
                TrackRow(
                    track_id=t.track_id,
                    cls_id=t.cls_id,
                    name=t.name,
                    conf=t.conf,
                    x1=t.x1,
                    y1=t.y1,
                    x2=t.x2,
                    y2=t.y2,
                )
            )
        for d in det_ins:
            key = (int(d.x1), int(d.y1), int(d.x2), int(d.y2))
            tid = id_by_box.get(key, -1)
            dets_out.append(
                Detection(
                    cls_id=d.cls_id,
                    conf=d.conf,
                    x1=d.x1,
                    y1=d.y1,
                    x2=d.x2,
                    y2=d.y2,
                    name=d.name,
                    track_id=tid,
                )
            )

        n_infer += 1
        if time.perf_counter() - t_window >= 1.0:
            infer_fps = n_infer / (time.perf_counter() - t_window)
            t_window = time.perf_counter()
            n_infer = 0

        # draw for PiP jpeg
        from studio.overlay import draw_overlay

        drawn = draw_overlay(
            bgr,
            dets_out,
            tracks_out,
            VisionHealth(True, 1, detail, stamp, infer_fps),
            "WORKER",
        )
        ok, buf = cv2.imencode(".jpg", drawn, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
        jpeg = buf.tobytes() if ok else b""

        pub.send(
            WorkerResult(
                stamp_s=stamp,
                health=VisionHealth(True, 1, detail, stamp, infer_fps),
                detections=dets_out,
                tracks=tracks_out,
                jpeg=jpeg,
            )
        )
        _ = t0  # silence lint; timing via infer_fps window


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        raise SystemExit(0)
