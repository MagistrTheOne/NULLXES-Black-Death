#!/usr/bin/env python3
"""Fetch extra HF UAV / hard-neg sets into cerber_v2 sources/."""

from __future__ import annotations

import argparse
import os
import shutil
import sys
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from _paths import PACK  # noqa: E402

# id → remap all box classes to CERBER uav=2 (or bird → skip / optional)
HF_SETS = {
    "pathikg/drone-detection-dataset": {"prefix": "pathikg", "mode": "uav"},
    "lll-a-p/fpv-drone-detection-dataset": {"prefix": "fpv", "mode": "uav"},
    "matisdsp/drone-bird-detection-dataset": {"prefix": "birdneg", "mode": "hardneg"},
    "ybli/yolo-drone-detection": {"prefix": "ybli", "mode": "uav"},
}

CERBER_UAV = 2
_IMG = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def _snapshot(repo_id: str, dest: Path, token: str | None) -> Path:
    from huggingface_hub import snapshot_download

    dest.mkdir(parents=True, exist_ok=True)
    print(f"HF {repo_id} → {dest}")
    snapshot_download(
        repo_id=repo_id,
        repo_type="dataset",
        local_dir=str(dest),
        token=token,
    )
    return dest


def _iter_pairs(root: Path) -> list[tuple[Path, Path]]:
    pairs: list[tuple[Path, Path]] = []
    lbls = {p.stem: p for p in root.rglob("*.txt") if p.is_file()}
    for img in root.rglob("*"):
        if not img.is_file() or img.suffix.lower() not in _IMG:
            continue
        lab = lbls.get(img.stem)
        if lab is None:
            cand = img.with_suffix(".txt")
            lab = cand if cand.is_file() else None
        if lab is not None:
            pairs.append((img, lab))
    return pairs


def _remap_uav(src: Path, dst: Path) -> int:
    n = 0
    lines: list[str] = []
    for line in src.read_text(encoding="utf-8", errors="ignore").splitlines():
        parts = line.split()
        if len(parts) < 5:
            continue
        parts[0] = str(CERBER_UAV)
        lines.append(" ".join(parts))
        n += 1
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
    return n


def merge_into_root(
    root: Path,
    src: Path,
    prefix: str,
    mode: str,
    val_ratio: float,
    seed: int,
) -> tuple[int, int]:
    import random

    pairs = _iter_pairs(src)
    if not pairs:
        print(f"  WARN: 0 pairs under {src}")
        return 0, 0
    rng = random.Random(seed)
    rng.shuffle(pairs)
    cut = max(1, int(len(pairs) * val_ratio))
    val_p, train_p = pairs[:cut], pairs[cut:]
    tr = va = 0
    for split, pool in (("train", train_p), ("val", val_p)):
        for img, lab in pool:
            if mode == "hardneg":
                # keep empty label (background hard-neg) — drop positive bird boxes
                name = f"{prefix}_{img.stem}{img.suffix}"
                img_dst = root / "images" / split / name
                lab_dst = root / "labels" / split / f"{prefix}_{img.stem}.txt"
                if not img_dst.exists():
                    shutil.copy2(img, img_dst)
                lab_dst.parent.mkdir(parents=True, exist_ok=True)
                lab_dst.write_text("", encoding="utf-8")
            else:
                name = f"{prefix}_{img.stem}{img.suffix}"
                img_dst = root / "images" / split / name
                lab_dst = root / "labels" / split / f"{prefix}_{img.stem}.txt"
                if not img_dst.exists():
                    shutil.copy2(img, img_dst)
                _remap_uav(lab, lab_dst)
            if split == "train":
                tr += 1
            else:
                va += 1
    print(f"  merged {prefix}: train+={tr} val+={va} mode={mode}")
    return tr, va


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--root", type=Path, required=True)
    p.add_argument("--hf-token", default=None)
    p.add_argument("--skip-download", action="store_true")
    p.add_argument("--sets", nargs="*", default=list(HF_SETS.keys()))
    p.add_argument("--val-ratio", type=float, default=0.12)
    p.add_argument("--seed", type=int, default=0)
    args = p.parse_args()

    token = args.hf_token or os.environ.get("HF_TOKEN")
    root = args.root
    sources = root / "sources" / "hf_extras"
    total_tr = total_va = 0

    for repo_id in args.sets:
        meta = HF_SETS.get(repo_id)
        if meta is None:
            print(f"skip unknown {repo_id}")
            continue
        dest = sources / meta["prefix"]
        if not args.skip_download:
            try:
                _snapshot(repo_id, dest, token)
            except Exception as exc:  # noqa: BLE001
                print(f"WARN download {repo_id}: {exc}")
                continue
        if not dest.is_dir():
            continue
        tr, va = merge_into_root(
            root, dest, meta["prefix"], meta["mode"], args.val_ratio, args.seed
        )
        total_tr += tr
        total_va += va

    print(f"HF extras done train+={total_tr} val+={total_va}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
