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
    out = args.out.expanduser()
    if not out.is_absolute():
        out = (Path.cwd() / out).resolve()
    else:
        out = out.resolve()
    out.parent.mkdir(parents=True, exist_ok=True)

    exported = model.export(format="onnx", imgsz=args.imgsz, opset=args.opset, simplify=True)
    exported_path = Path(str(exported)).resolve()
    if exported_path != out:
        out.write_bytes(exported_path.read_bytes())

    digest = sha256_file(out)
    cfg = {}
    cfg_path = args.config.expanduser()
    if not cfg_path.is_absolute():
        cfg_path = (Path.cwd() / cfg_path).resolve()
    if cfg_path.exists():
        cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
    try:
        model_path = str(out.relative_to(ROOT.resolve())).replace("\\", "/")
    except ValueError:
        model_path = str(out)
    cfg["model_path"] = model_path
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
    cfg_path.parent.mkdir(parents=True, exist_ok=True)
    cfg_path.write_text(yaml.safe_dump(cfg, sort_keys=False), encoding="utf-8")
    print(f"onnx={out}")
    print(f"sha256={digest}")
    print(f"num_classes={len(cfg.get('classes') or [])}")


if __name__ == "__main__":
    main()
