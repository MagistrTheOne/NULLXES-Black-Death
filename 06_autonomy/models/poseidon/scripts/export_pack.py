#!/usr/bin/env python3
"""Export a POSEIDON pack: Ultralytics best.pt → model.onnx + sha in pack.yaml.

Run on NULLXES GPU servers only.

  python 06_autonomy/models/poseidon/scripts/export_pack.py \\
    --pack uav_seraphim --weights path/to/best.pt
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[4]


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser(description="POSEIDON pack ONNX export")
    ap.add_argument("--pack", required=True, help="pack_id under models/poseidon/packs/")
    ap.add_argument("--weights", required=True, type=Path, help="Ultralytics best.pt")
    ap.add_argument("--imgsz", type=int, default=640)
    ap.add_argument("--opset", type=int, default=17)
    args = ap.parse_args()

    pack_dir = REPO / "06_autonomy" / "models" / "poseidon" / "packs" / args.pack
    yaml_path = pack_dir / "pack.yaml"
    if not yaml_path.is_file():
        print(f"BLOCKED: missing {yaml_path}", file=sys.stderr)
        return 1
    if not args.weights.is_file():
        print(f"BLOCKED: missing weights {args.weights}", file=sys.stderr)
        return 1

    from ultralytics import YOLO

    model = YOLO(str(args.weights))
    out_onnx = pack_dir / "model.onnx"
    exported = model.export(
        format="onnx", imgsz=args.imgsz, opset=args.opset, simplify=True
    )
    exported_path = Path(str(exported))
    if exported_path.resolve() != out_onnx.resolve():
        out_onnx.write_bytes(exported_path.read_bytes())

    digest = _sha256(out_onnx)
    with open(yaml_path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    data["sha256"] = digest
    data["model_path"] = "model.onnx"
    with open(yaml_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, sort_keys=False)

    print(f"pack={args.pack} onnx={out_onnx} sha256={digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
