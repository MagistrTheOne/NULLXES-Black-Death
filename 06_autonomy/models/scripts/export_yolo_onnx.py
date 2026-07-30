#!/usr/bin/env python3
"""Export Ultralytics YOLO .pt → ONNX and write sha256 into detector config."""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CFG = ROOT / "06_autonomy" / "models" / "configs" / "detector_alpha.yaml"
DEFAULT_OUT = ROOT / "06_autonomy" / "models" / "onnx" / "detector_alpha.onnx"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--weights", required=True, help="path to .pt")
    p.add_argument("--out", type=Path, default=DEFAULT_OUT)
    p.add_argument("--config", type=Path, default=DEFAULT_CFG)
    p.add_argument("--imgsz", type=int, default=640)
    p.add_argument("--opset", type=int, default=17)
    args = p.parse_args()

    try:
        from ultralytics import YOLO
    except ImportError:
        print("pip install ultralytics (torch from pod image)", file=sys.stderr)
        sys.exit(1)

    model = YOLO(args.weights)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    exported = model.export(format="onnx", imgsz=args.imgsz, opset=args.opset, simplify=True)
    exported_path = Path(str(exported))
    if exported_path.resolve() != args.out.resolve():
        args.out.write_bytes(exported_path.read_bytes())

    digest = sha256_file(args.out)
    cfg = {}
    if args.config.exists():
        cfg = yaml.safe_load(args.config.read_text(encoding="utf-8")) or {}
    cfg["model_path"] = str(args.out.relative_to(ROOT)).replace("\\", "/")
    cfg["sha256"] = digest
    cfg["onnx_layout"] = "yolo_v8_raw"
    cfg["input_name"] = "images"
    cfg["output_name"] = "output0"
    cfg["input_size"] = [args.imgsz, args.imgsz]
    if "classes" not in cfg or not cfg["classes"]:
        names = getattr(model, "names", None)
        if isinstance(names, dict):
            cfg["classes"] = [names[i] for i in sorted(names.keys())]
        elif isinstance(names, (list, tuple)):
            cfg["classes"] = list(names)
    args.config.write_text(yaml.safe_dump(cfg, sort_keys=False), encoding="utf-8")
    print(f"onnx={args.out}")
    print(f"sha256={digest}")
    print(f"num_classes={len(cfg.get('classes') or [])}")


if __name__ == "__main__":
    main()
