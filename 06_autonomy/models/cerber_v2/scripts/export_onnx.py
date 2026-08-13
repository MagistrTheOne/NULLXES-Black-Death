#!/usr/bin/env python3
"""Export CERBER V2 pursuit best.pt → detector_alpha_v2b.onnx + sha256."""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

import yaml

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from _paths import CONFIGS, REPO  # noqa: E402


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--weights", type=Path, required=True)
    p.add_argument("--train-config", type=Path, default=CONFIGS / "train.yaml")
    p.add_argument("--imgsz", type=int, default=None)
    p.add_argument("--opset", type=int, default=None)
    args = p.parse_args()

    cfg = yaml.safe_load(args.train_config.read_text(encoding="utf-8"))
    cfg_dir = args.train_config.resolve().parent
    pack_cfg = Path(cfg.get("flight_config", "detector_alpha_v2b.yaml"))
    if not pack_cfg.is_file():
        pack_cfg = cfg_dir / Path(pack_cfg).name
    flight_cfg = pack_cfg
    onnx_rel = str(cfg.get("flight_onnx", "../../onnx/detector_alpha_v2b.onnx"))
    out = Path(onnx_rel)
    if not out.is_absolute():
        out = (cfg_dir / onnx_rel).resolve()
    runtime_cfg = REPO / "06_autonomy" / "models" / "configs" / flight_cfg.name

    weights = args.weights
    if not weights.is_file():
        print(f"BLOCKED: missing {weights}", file=sys.stderr)
        return 1

    try:
        from ultralytics import YOLO
    except ImportError:
        print("BLOCKED: ultralytics required", file=sys.stderr)
        return 1

    imgsz = int(args.imgsz or cfg.get("export_imgsz", 640))
    opset = int(args.opset or cfg.get("export_opset", 17))
    model = YOLO(str(weights))
    out.parent.mkdir(parents=True, exist_ok=True)
    exported = model.export(format="onnx", imgsz=imgsz, opset=opset, simplify=True)
    exported_path = Path(str(exported)).resolve()
    out.write_bytes(exported_path.read_bytes())
    digest = sha256_file(out)

    base = {}
    if flight_cfg.is_file():
        base = yaml.safe_load(flight_cfg.read_text(encoding="utf-8")) or {}
    base["model_path"] = f"06_autonomy/models/onnx/{out.name}"
    base["sha256"] = digest
    base["onnx_layout"] = "yolo_v8_raw"
    base["input_name"] = "images"
    base["output_name"] = "output0"
    base["input_size"] = [imgsz, imgsz]
    base.setdefault(
        "classes",
        [
            "human",
            "vehicle",
            "uav",
            "landing_zone",
            "obstacle",
            "power_line",
            "road",
            "building",
            "forest",
            "water",
            "fire",
            "infrastructure",
            "cargo",
        ],
    )
    base.setdefault(
        "providers",
        ["CUDAExecutionProvider", "CPUExecutionProvider"],
    )
    text = yaml.safe_dump(base, sort_keys=False)
    flight_cfg.write_text(text, encoding="utf-8")
    runtime_cfg.write_text(text, encoding="utf-8")

    print(f"onnx={out}")
    print(f"sha256={digest}")
    print(f"config={flight_cfg}")
    print(f"runtime_config={runtime_cfg}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
