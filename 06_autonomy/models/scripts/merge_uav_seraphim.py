#!/usr/bin/env python3
"""Download Seraphim drone YOLO (HF) and merge as CERBER class uav=2.

Default: test/ only (~8k) — fits a ~2h RunPod leftover window.
Full train/ is ~9GB — use --full only when you have disk + time.

  python merge_uav_seraphim.py --root /workspace/datasets/cerber
  python merge_uav_seraphim.py --root ... --full --max-train 15000
"""

from __future__ import annotations

import argparse
import os
import random
import shutil
import sys
from pathlib import Path

HF_UAV_YOLO = "lgrzybowski/seraphim-drone-detection-dataset"
CERBER_UAV = 2


def _remap_to_uav(src: Path, dst: Path) -> None:
    lines_out: list[str] = []
    for line in src.read_text(encoding="utf-8").splitlines():
        parts = line.split()
        if len(parts) < 5:
            continue
        parts[0] = str(CERBER_UAV)
        lines_out.append(" ".join(parts))
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text("\n".join(lines_out) + ("\n" if lines_out else ""), encoding="utf-8")


def _iter_yolo_pairs(split_dir: Path) -> list[tuple[Path, Path]]:
    """Seraphim layout: train|test/{images,labels} or flat images+labels."""
    pairs: list[tuple[Path, Path]] = []
    img_dir = split_dir / "images"
    lbl_dir = split_dir / "labels"
    if img_dir.is_dir() and lbl_dir.is_dir():
        for img in img_dir.glob("*.*"):
            if img.suffix.lower() not in {".jpg", ".jpeg", ".png", ".bmp", ".webp"}:
                continue
            lab = lbl_dir / f"{img.stem}.txt"
            if lab.is_file():
                pairs.append((img, lab))
        return pairs
    # flat: *.jpg next to *.txt
    for img in split_dir.rglob("*.*"):
        if img.suffix.lower() not in {".jpg", ".jpeg", ".png", ".bmp", ".webp"}:
            continue
        lab = img.with_suffix(".txt")
        if not lab.is_file():
            lab = split_dir / "labels" / f"{img.stem}.txt"
        if lab.is_file():
            pairs.append((img, lab))
    return pairs


def fetch(dest: Path, token: str | None, full: bool) -> Path:
    from huggingface_hub import snapshot_download

    dest.mkdir(parents=True, exist_ok=True)
    patterns = ["test/**", "README.md", "LICENSE"]
    if full:
        patterns = ["train/**", "test/**", "README.md", "LICENSE"]
    print(f"HF snapshot {HF_UAV_YOLO} patterns={patterns}")
    snapshot_download(
        repo_id=HF_UAV_YOLO,
        repo_type="dataset",
        local_dir=str(dest),
        token=token,
        allow_patterns=patterns,
    )
    return dest


def merge(
    root: Path,
    src_root: Path,
    *,
    full: bool,
    max_train: int,
    val_ratio: float,
    seed: int,
) -> tuple[int, int]:
    rng = random.Random(seed)
    train_n = val_n = 0

    test_dir = src_root / "test"
    train_dir = src_root / "train"

    test_pairs = _iter_yolo_pairs(test_dir) if test_dir.is_dir() else []
    train_pairs = _iter_yolo_pairs(train_dir) if full and train_dir.is_dir() else []

    if not test_pairs and not train_pairs:
        # maybe downloaded flat
        test_pairs = _iter_yolo_pairs(src_root)

    if full and train_pairs:
        rng.shuffle(train_pairs)
        train_pairs = train_pairs[:max_train]
        pool_train, pool_val = train_pairs, test_pairs
        if not pool_val and pool_train:
            rng.shuffle(pool_train)
            cut = max(1, int(len(pool_train) * val_ratio))
            pool_val = pool_train[:cut]
            pool_train = pool_train[cut:]
    else:
        # time-budget mode: split test/ into train+val
        rng.shuffle(test_pairs)
        cut = max(1, int(len(test_pairs) * val_ratio))
        pool_val = test_pairs[:cut]
        pool_train = test_pairs[cut:]

    for split, pairs in (("train", pool_train), ("val", pool_val)):
        for img, lab in pairs:
            name = f"uav_{img.stem}{img.suffix}"
            img_dst = root / "images" / split / name
            lab_dst = root / "labels" / split / f"uav_{img.stem}.txt"
            if not img_dst.exists():
                shutil.copy2(img, img_dst)
            _remap_to_uav(lab, lab_dst)
            if split == "train":
                train_n += 1
            else:
                val_n += 1

    # invalidate caches so YOLO rescan
    for cache in (root / "labels" / "train.cache", root / "labels" / "val.cache"):
        if cache.is_file():
            cache.unlink()
            print(f"removed {cache}")

    return train_n, val_n


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--root", type=Path, required=True)
    p.add_argument("--full", action="store_true", help="also download train/ (~9GB)")
    p.add_argument("--max-train", type=int, default=12000)
    p.add_argument("--val-ratio", type=float, default=0.15)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--hf-token", default=None)
    p.add_argument("--skip-download", action="store_true")
    args = p.parse_args()

    root = args.root
    src = root / "sources" / "seraphim_uav"
    token = args.hf_token or os.environ.get("HF_TOKEN")

    if not args.skip_download:
        try:
            fetch(src, token, args.full)
        except Exception as exc:  # noqa: BLE001
            print(f"BLOCKED download: {exc}", file=sys.stderr)
            return 1

    n_tr, n_va = merge(
        root,
        src,
        full=args.full,
        max_train=args.max_train,
        val_ratio=args.val_ratio,
        seed=args.seed,
    )
    print(f"merged uav=2 train+={n_tr} val+={n_va}")
    print("next: fine-tune from best.pt (keep VisDrone images already in root)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
