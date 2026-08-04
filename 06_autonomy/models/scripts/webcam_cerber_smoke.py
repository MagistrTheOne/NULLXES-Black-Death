#!/usr/bin/env python3
"""CERBER host webcam smoke — OpenCV cam → VisionPipeline (ORT) → boxes.

Not robot. Not Ultralytics runtime. Stage-2 live camera check.

  python 06_autonomy/models/scripts/webcam_cerber_smoke.py
  python 06_autonomy/models/scripts/webcam_cerber_smoke.py --v2 --cam 0
  python 06_autonomy/models/scripts/webcam_cerber_smoke.py --conf 0.25

q / ESC = quit
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import cv2

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "06_autonomy"))

from perception.vision.vision_node import VisionPipeline  # noqa: E402


def _draw(frame, dets, names: list[str]) -> None:
    for d in dets:
        x1, y1, x2, y2 = (int(d.x1), int(d.y1), int(d.x2), int(d.y2))
        name = names[d.class_id] if 0 <= d.class_id < len(names) else str(d.class_id)
        label = f"{name} {d.confidence:.2f}"
        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 220, 80), 2)
        cv2.putText(
            frame,
            label,
            (x1, max(16, y1 - 6)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (0, 220, 80),
            2,
            cv2.LINE_AA,
        )


def main() -> int:
    ap = argparse.ArgumentParser(description="CERBER webcam smoke (aerial ONNX)")
    ap.add_argument("--v2", action="store_true", help="use detector_alpha_v2 (+uav)")
    ap.add_argument(
        "--v2b",
        action="store_true",
        help="use detector_alpha_v2b (pursuit boost, after RunPod export)",
    )
    ap.add_argument("--cam", type=int, default=0, help="OpenCV camera index")
    ap.add_argument("--conf", type=float, default=None, help="override confidence")
    args = ap.parse_args()

    if args.v2b:
        cfg_name = "detector_alpha_v2b.yaml"
    elif args.v2:
        cfg_name = "detector_alpha_v2.yaml"
    else:
        cfg_name = "detector_alpha.yaml"
    cfg_path = REPO / "06_autonomy" / "models" / "configs" / cfg_name

    print(f"repo: {REPO}")
    print(f"config: {cfg_path}")
    pipe = VisionPipeline(cfg_path)
    if args.conf is not None:
        object.__setattr__(pipe.engine.cfg, "confidence", float(args.conf))

    # Prefer headful OpenCV (not headless) for imshow
    cap = cv2.VideoCapture(args.cam, cv2.CAP_DSHOW)
    if not cap.isOpened():
        cap = cv2.VideoCapture(args.cam)
    if not cap.isOpened():
        print(f"BLOCKED: cannot open camera index {args.cam}")
        return 1

    names = pipe.names
    print(f"classes (trained useful): human, vehicle" + (" , uav" if args.v2 else ""))
    print(f"conf={pipe.engine.cfg.confidence}  providers={pipe.engine.cfg.providers}")
    print("window open — stand in frame; q/ESC quit")

    t0 = time.perf_counter()
    n = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            print("BLOCKED: camera frame read failed")
            break
        dets = pipe.process_bgr(frame)
        _draw(frame, dets, names)
        n += 1
        dt = time.perf_counter() - t0
        fps = n / dt if dt > 0 else 0.0
        counts: dict[str, int] = {}
        for d in dets:
            name = names[d.class_id] if 0 <= d.class_id < len(names) else "?"
            counts[name] = counts.get(name, 0) + 1
        hud = f"CERBER {'v2' if args.v2 else 'v1'}  FPS={fps:.1f}  " + (
            " ".join(f"{k}:{v}" for k, v in sorted(counts.items())) or "—"
        )
        cv2.putText(
            frame, hud, (8, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (40, 40, 255), 2, cv2.LINE_AA
        )
        cv2.imshow("CERBER webcam smoke", frame)
        key = cv2.waitKey(1) & 0xFF
        if key in (27, ord("q")):
            break

    cap.release()
    cv2.destroyAllWindows()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
