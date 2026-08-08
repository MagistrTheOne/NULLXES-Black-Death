#!/usr/bin/env python3
"""Train one POSEIDON pack on host image torch (do not pip-install torch)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[4]
CONFIGS = REPO / "06_autonomy" / "models" / "poseidon" / "configs"


def _require_image_torch() -> None:
    try:
        import torch
    except ImportError as exc:
        raise SystemExit(
            "BLOCKED: torch not found. Use a PyTorch CUDA machine image. "
            "Do NOT pip install torch for POSEIDON train."
        ) from exc
    if not torch.cuda.is_available():
        print("WARN: CUDA not available — train will be slow/CPU", file=sys.stderr)
    else:
        print(f"torch={torch.__version__} device={torch.cuda.get_device_name(0)}")


def main() -> int:
    ap = argparse.ArgumentParser(description="POSEIDON pack train (Ultralytics)")
    ap.add_argument("--train-config", type=Path, required=True)
    ap.add_argument("--data", type=Path, required=True, help="YOLO data.yaml for this pack")
    ap.add_argument("--weights", type=Path, default=None)
    ap.add_argument("--epochs", type=int, default=None)
    ap.add_argument("--batch", type=int, default=None)
    ap.add_argument("--imgsz", type=int, default=None)
    ap.add_argument("--device", default=None)
    args = ap.parse_args()

    _require_image_torch()

    cfg = yaml.safe_load(args.train_config.read_text(encoding="utf-8"))
    data = Path(args.data)
    if not data.is_file():
        print(f"BLOCKED: missing data.yaml {data}", file=sys.stderr)
        return 1

    weights = args.weights or Path(str(cfg.get("base_weights", "yolov8s.pt")))
    from ultralytics import YOLO

    model = YOLO(str(weights))
    model.train(
        data=str(data),
        project=str(cfg.get("project", "poseidon")),
        name=str(cfg.get("run_name", cfg.get("pack_id", "pack"))),
        epochs=int(args.epochs or cfg.get("epochs", 80)),
        batch=int(args.batch or cfg.get("batch", 16)),
        imgsz=int(args.imgsz or cfg.get("imgsz", 640)),
        device=args.device if args.device is not None else cfg.get("device", 0),
        workers=int(cfg.get("workers", 8)),
        exist_ok=True,
    )
    print(f"done pack={cfg.get('pack_id')} → runs/detect/{cfg.get('run_name')}/weights/best.pt")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
