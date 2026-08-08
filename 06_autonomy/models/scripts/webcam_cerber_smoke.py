#!/usr/bin/env python3
"""CERBER host webcam smoke — OpenCV cam → VisionPipeline (ORT) → boxes.

Not robot. Not Ultralytics runtime. Stage-2 live camera check.

  python 06_autonomy/models/scripts/webcam_cerber_smoke.py
  python 06_autonomy/models/scripts/webcam_cerber_smoke.py --v2 --cam 0
  python 06_autonomy/models/scripts/webcam_cerber_smoke.py --conf 0.25

Keys:
  F1 / O  — overlay ON  (boxes + stage HUD)
  F2      — overlay OFF (bare frame; still runs detect)
  q / ESC — quit
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

# OpenCV waitKeyEx F-keys (Windows / Linux)
_F1 = {0x700000, 7340032, 65470}
_F2 = {0x710000, 7405568, 65471}


def _ema(prev: float, sample: float, a: float = 0.15) -> float:
    return sample if prev <= 0.0 else ((1.0 - a) * prev + a * sample)


def _draw_boxes(frame, dets, names: list[str]) -> None:
    for d in dets:
        x1, y1, x2, y2 = (int(d.x1), int(d.y1), int(d.x2), int(d.y2))
        name = names[d.cls_id] if 0 <= d.cls_id < len(names) else str(d.cls_id)
        label = f"{name} {d.conf:.2f}"
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


def _draw_hud(frame, lines: list[str]) -> None:
    x, y0, dy = 8, 22, 20
    for i, line in enumerate(lines):
        y = y0 + i * dy
        cv2.putText(
            frame, line, (x, y), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 0), 3, cv2.LINE_AA
        )
        cv2.putText(
            frame, line, (x, y), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (40, 40, 255), 1, cv2.LINE_AA
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
    ap.add_argument(
        "--only",
        default="",
        help="comma class filter for draw/HUD (e.g. human). Mapping is not remapped.",
    )
    ap.add_argument(
        "--overlay-off",
        action="store_true",
        help="start with overlay OFF (F1 to enable)",
    )
    args = ap.parse_args()
    only = {s.strip() for s in args.only.split(",") if s.strip()}

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

    cap = cv2.VideoCapture(args.cam, cv2.CAP_DSHOW)
    if not cap.isOpened():
        cap = cv2.VideoCapture(args.cam)
    if not cap.isOpened():
        print(f"BLOCKED: cannot open camera index {args.cam}")
        return 1

    names = pipe.names
    tag = "v2b" if args.v2b else ("v2" if args.v2 else "v1")
    raw = getattr(getattr(pipe.engine, "_session", None), "_session", None)
    providers = (
        tuple(raw.get_providers())
        if raw is not None and hasattr(raw, "get_providers")
        else tuple(pipe.engine.cfg.providers)
    )
    print(f"CERBER {tag}  conf={pipe.engine.cfg.confidence}  providers={providers}")
    if only:
        print(f"draw filter: {sorted(only)}")
    print("NOTE: aerial VisDrone weights — close-up webcam is OOD")
    if "CUDAExecutionProvider" not in providers:
        print("WARN: CUDA EP inactive — inference on CPU")
    print("F1/O overlay ON · F2 overlay OFF · q/ESC quit")

    overlay = not args.overlay_off
    ema = {
        "capture_ms": 0.0,
        "preprocess_ms": 0.0,
        "inference_ms": 0.0,
        "nms_ms": 0.0,
        "render_ms": 0.0,
        "total_ms": 0.0,
    }
    fps_ema = 0.0
    n = 0

    while True:
        t_loop = time.perf_counter()

        t0 = time.perf_counter()
        ok, frame = cap.read()
        capture_ms = (time.perf_counter() - t0) * 1000.0
        if not ok:
            print("BLOCKED: camera frame read failed")
            break

        dets, stages = pipe.engine.infer_timed(frame)

        shown = [
            d
            for d in dets
            if not only
            or (names[d.cls_id] if 0 <= d.cls_id < len(names) else "?") in only
        ]

        t_r0 = time.perf_counter()
        if overlay:
            _draw_boxes(frame, shown, names)
            counts: dict[str, int] = {}
            for d in dets:
                name = names[d.cls_id] if 0 <= d.cls_id < len(names) else "?"
                counts[name] = counts.get(name, 0) + 1
            count_s = " ".join(f"{k}:{v}" for k, v in sorted(counts.items())) or "—"
            hud = [
                f"CERBER {tag}  EP={providers[0]}",
                f"Capture:    {ema['capture_ms']:5.1f} ms",
                f"Preprocess: {ema['preprocess_ms']:5.1f} ms",
                f"Inference:  {ema['inference_ms']:5.1f} ms",
                f"NMS:        {ema['nms_ms']:5.1f} ms",
                f"Render:     {ema['render_ms']:5.1f} ms",
                f"Total:      {ema['total_ms']:5.1f} ms",
                f"FPS:        {fps_ema:5.1f}",
                f"Dets: {count_s}",
                "F1 overlay ON · F2 OFF",
            ]
            _draw_hud(frame, hud)
        render_ms = (time.perf_counter() - t_r0) * 1000.0

        cv2.imshow("CERBER webcam smoke", frame)

        total_ms = (time.perf_counter() - t_loop) * 1000.0
        n += 1
        ema["capture_ms"] = _ema(ema["capture_ms"], capture_ms)
        ema["preprocess_ms"] = _ema(ema["preprocess_ms"], stages["preprocess_ms"])
        ema["inference_ms"] = _ema(ema["inference_ms"], stages["inference_ms"])
        ema["nms_ms"] = _ema(ema["nms_ms"], stages["nms_ms"])
        ema["render_ms"] = _ema(ema["render_ms"], render_ms)
        ema["total_ms"] = _ema(ema["total_ms"], total_ms)
        inst_fps = 1000.0 / total_ms if total_ms > 0 else 0.0
        fps_ema = _ema(fps_ema, inst_fps)

        key = cv2.waitKeyEx(1)
        if key in (27, ord("q"), ord("Q")):
            break
        if key in _F1 or key in (ord("o"), ord("O")):
            overlay = True
        elif key in _F2:
            overlay = False

    cap.release()
    cv2.destroyAllWindows()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
