#!/usr/bin/env python3
"""Train CERBER V2 pursuit detect on RunPod (Ultralytics, bare metal)."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import yaml

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from _paths import CONFIGS, REPO  # noqa: E402


def _resolve_weights(cfg: dict, override: Path | None) -> Path:
    if override is not None:
        if not override.is_file():
            raise FileNotFoundError(override)
        return override.resolve()

    local = REPO / str(cfg.get("base_weights", ""))
    if local.is_file():
        return local.resolve()

    # cwd-relative (if trained earlier on pod)
    cand = Path(cfg.get("base_weights", ""))
    if cand.is_file():
        return cand.resolve()

    hub = cfg.get("hub_fallback", "MagistrTheOne/CERBER-CV-v2")
    print(f"local weights missing → HF hub download {hub}")
    from huggingface_hub import hf_hub_download

    # try common weight filenames
    for name in ("best.pt", "weights/best.pt", "CERBER-CV-v2.pt", "model.pt"):
        try:
            path = hf_hub_download(
                repo_id=hub,
                filename=name,
                token=os.environ.get("HF_TOKEN"),
            )
            print(f"hub file={name} → {path}")
            return Path(path)
        except Exception:  # noqa: BLE001
            continue
    raise FileNotFoundError(
        f"BLOCKED: no local {cfg.get('base_weights')} and Hub {hub} has no best.pt — "
        "pass --weights explicitly"
    )


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--train-config", type=Path, default=CONFIGS / "train.yaml")
    p.add_argument("--data", type=Path, default=None)
    p.add_argument("--weights", type=Path, default=None)
    p.add_argument("--epochs", type=int, default=None)
    p.add_argument("--batch", type=int, default=None)
    p.add_argument("--imgsz", type=int, default=None)
    p.add_argument("--device", default=None)
    args = p.parse_args()

    cfg = yaml.safe_load(args.train_config.read_text(encoding="utf-8"))
    data = args.data
    if data is None:
        env_root = os.environ.get("CERBER_V2_ROOT")
        if env_root and (Path(env_root) / "data.yaml").is_file():
            data = Path(env_root) / "data.yaml"
        else:
            data = CONFIGS / "data.yaml"
    data = Path(data)
    if not data.is_file():
        print(f"BLOCKED: missing {data} — run prepare_data.py", file=sys.stderr)
        return 1

    try:
        from ultralytics import YOLO
    except ImportError:
        print("BLOCKED: pip install ultralytics (torch from pod image)", file=sys.stderr)
        return 1

    try:
        weights = _resolve_weights(cfg, args.weights)
    except FileNotFoundError as exc:
        print(f"BLOCKED: {exc}", file=sys.stderr)
        return 1

    print(f"weights={weights}")
    print(f"data={data}")
    model = YOLO(str(weights))
    results = model.train(
        data=str(data.resolve()),
        imgsz=int(args.imgsz or cfg["imgsz"]),
        epochs=int(args.epochs or cfg["epochs"]),
        batch=int(args.batch or cfg["batch"]),
        device=args.device if args.device is not None else cfg.get("device", 0),
        workers=int(cfg.get("workers", 8)),
        project=str(cfg.get("project", "cerber-detect")),
        name=str(cfg.get("run_name", "v2-pursuit")),
        exist_ok=True,
    )
    best = Path(results.save_dir) / "weights" / "best.pt"
    print(f"best={best}")
    print("next: python export_onnx.py --weights", best)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
