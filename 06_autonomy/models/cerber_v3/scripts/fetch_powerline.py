#!/usr/bin/env python3
"""HF docmhvr/powerline-components-and-faults → CERBER power_line=5 YOLO tree."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

CERBER_POWER = 5
REPO = "docmhvr/powerline-components-and-faults"


def _xyxy_to_yolo(x1: float, y1: float, x2: float, y2: float, w: int, h: int) -> str:
    bw = max(1e-6, w)
    bh = max(1e-6, h)
    cx = ((x1 + x2) / 2.0) / bw
    cy = ((y1 + y2) / 2.0) / bh
    ww = abs(x2 - x1) / bw
    hh = abs(y2 - y1) / bh
    return f"{CERBER_POWER} {cx:.6f} {cy:.6f} {ww:.6f} {hh:.6f}"


def merge_split(ds_split, root: Path, split: str) -> int:
    n = 0
    img_dir = root / "images" / split
    lab_dir = root / "labels" / split
    img_dir.mkdir(parents=True, exist_ok=True)
    lab_dir.mkdir(parents=True, exist_ok=True)
    for i, ex in enumerate(ds_split):
        im = ex["image"]
        w, h = im.size
        boxes = ex.get("bboxes") or []
        stem = f"pl_{split}_{i:06d}"
        img_path = img_dir / f"{stem}.jpg"
        if not img_path.is_file():
            rgb = im.convert("RGB")
            rgb.save(img_path, quality=92)
        lines = [_xyxy_to_yolo(*map(float, b[:4]), w, h) for b in boxes if len(b) >= 4]
        (lab_dir / f"{stem}.txt").write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
        n += 1
    return n


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--root", type=Path, required=True)
    p.add_argument("--hf-token", default=None)
    args = p.parse_args()
    token = args.hf_token or os.environ.get("HF_TOKEN")
    try:
        from datasets import load_dataset
    except ImportError:
        print("BLOCKED: pip install datasets")
        return 1
    print(f"HF {REPO} → {args.root} class={CERBER_POWER}")
    ds = load_dataset(REPO, token=token)
    tr = merge_split(ds["train"], args.root, "train") if "train" in ds else 0
    va_split = ds["validation"] if "validation" in ds else ds.get("test")
    va = merge_split(va_split, args.root, "val") if va_split is not None else 0
    print(f"powerline merged train+={tr} val+={va}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
