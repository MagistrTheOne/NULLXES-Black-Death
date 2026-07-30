#!/usr/bin/env python3
"""Train CERBER detect head (Ultralytics) then optional ONNX export for flight.

On RunPod PyTorch images, torch is preinstalled — only:
  pip install -r 06_autonomy/models/requirements-train.txt

  python prepare_cerber_data.py --root /workspace/datasets/cerber
  python train_cerber_detect.py --data /workspace/datasets/cerber/data.yaml
  python train_cerber_detect.py --data ... --export
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[3]
DEFAULT_TRAIN_CFG = REPO / "06_autonomy" / "models" / "configs" / "cerber_train.yaml"


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--train-config", type=Path, default=DEFAULT_TRAIN_CFG)
    p.add_argument("--data", type=Path, default=None, help="override data.yaml")
    p.add_argument("--export", action="store_true", help="export best.pt → flight ONNX")
    p.add_argument("--epochs", type=int, default=None)
    p.add_argument("--batch", type=int, default=None)
    p.add_argument("--imgsz", type=int, default=None)
    p.add_argument("--device", default=None)
    args = p.parse_args()

    cfg = yaml.safe_load(args.train_config.read_text(encoding="utf-8"))
    data = args.data or (REPO / str(cfg["data_yaml"]))
    if not Path(data).is_file():
        print(
            f"BLOCKED: missing {data}. Run prepare_cerber_data.py first.",
            file=sys.stderr,
        )
        return 1

    try:
        from ultralytics import YOLO
    except ImportError:
        print(
            "BLOCKED: pip install ultralytics "
            "(torch must already exist — e.g. RunPod pytorch image)",
            file=sys.stderr,
        )
        return 1

    model = YOLO(str(cfg.get("base_weights", "yolov8s.pt")))
    results = model.train(
        data=str(data),
        imgsz=int(args.imgsz or cfg["imgsz"]),
        epochs=int(args.epochs or cfg["epochs"]),
        batch=int(args.batch or cfg["batch"]),
        device=args.device if args.device is not None else cfg.get("device", 0),
        workers=int(cfg.get("workers", 8)),
        project=str(cfg.get("project", "cerber-detect")),
        name=str(cfg.get("run_name", "v1")),
        exist_ok=True,
    )
    best = Path(results.save_dir) / "weights" / "best.pt"
    print(f"best={best}")

    if args.export:
        export_script = REPO / "06_autonomy" / "models" / "scripts" / "export_yolo_onnx.py"
        flight_cfg = REPO / str(cfg["flight_config"])
        cmd = [
            sys.executable,
            str(export_script),
            "--weights",
            str(best),
            "--config",
            str(flight_cfg),
            "--imgsz",
            str(cfg.get("export_imgsz", 640)),
            "--opset",
            str(cfg.get("export_opset", 17)),
        ]
        print(" ", " ".join(cmd))
        return subprocess.call(cmd)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
