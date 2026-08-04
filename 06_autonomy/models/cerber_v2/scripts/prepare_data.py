#!/usr/bin/env python3
"""Build CERBER V2 YOLO tree on RunPod (VisDrone + Seraphim + HF extras + local UAV)."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

import yaml

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from _paths import CONFIGS, PACK, REPO, SCRIPTS  # noqa: E402

CERBER_UAV = 2
_IMG = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def _write_data_yaml(root: Path) -> Path:
    tpl = CONFIGS / "data.yaml"
    cfg = yaml.safe_load(tpl.read_text(encoding="utf-8"))
    cfg["path"] = str(root.resolve())
    out = root / "data.yaml"
    out.write_text(yaml.safe_dump(cfg, sort_keys=False), encoding="utf-8")
    # also refresh pack template path for convenience
    tpl.write_text(yaml.safe_dump(cfg, sort_keys=False), encoding="utf-8")
    print(f"data.yaml → {out}")
    return out


def _ensure_splits(root: Path) -> None:
    for split in ("train", "val"):
        (root / "images" / split).mkdir(parents=True, exist_ok=True)
        (root / "labels" / split).mkdir(parents=True, exist_ok=True)


def run_visdrone(root: Path) -> None:
    prep = REPO / "06_autonomy" / "models" / "scripts" / "prepare_cerber_data.py"
    cmd = [
        sys.executable,
        str(prep),
        "--root",
        str(root),
        "--skip-hf",
    ]
    print(" ", " ".join(cmd))
    rc = subprocess.call(cmd)
    if rc != 0:
        raise RuntimeError(f"prepare_cerber_data VisDrone failed rc={rc}")


def run_seraphim(root: Path, full: bool, token: str | None) -> None:
    merge = REPO / "06_autonomy" / "models" / "scripts" / "merge_uav_seraphim.py"
    cmd = [sys.executable, str(merge), "--root", str(root), "--max-train", "20000"]
    if full:
        cmd.append("--full")
    if token:
        cmd.extend(["--hf-token", token])
    print(" ", " ".join(cmd[:-2] if token else cmd), ("--hf-token ***" if token else ""))
    rc = subprocess.call(cmd)
    if rc != 0:
        raise RuntimeError(f"merge_uav_seraphim failed rc={rc}")


def run_hf_extras(root: Path, token: str | None, skip_dl: bool) -> None:
    cmd = [
        sys.executable,
        str(SCRIPTS / "fetch_hf_extras.py"),
        "--root",
        str(root),
    ]
    if token:
        cmd.extend(["--hf-token", token])
    if skip_dl:
        cmd.append("--skip-download")
    print(" ", " ".join(c if c != token else "***" for c in cmd))
    rc = subprocess.call(cmd, cwd=str(SCRIPTS))
    if rc != 0:
        print(f"WARN: HF extras rc={rc} (continuing)")


def _iter_pairs(root: Path) -> list[tuple[Path, Path]]:
    pairs: list[tuple[Path, Path]] = []
    lbls = {p.stem: p for p in root.rglob("*.txt") if p.is_file()}
    for img in root.rglob("*"):
        if not img.is_file() or img.suffix.lower() not in _IMG:
            continue
        lab = lbls.get(img.stem) or (
            img.with_suffix(".txt") if img.with_suffix(".txt").is_file() else None
        )
        if lab is not None:
            pairs.append((img, lab))
    return pairs


def merge_local_uav(root: Path) -> tuple[int, int]:
    """Merge sources/dut_anti_uav and sources/uett4k if present (all → uav=2)."""
    tr = va = 0
    for name in ("dut_anti_uav", "uett4k"):
        src = root / "sources" / name
        if not src.is_dir():
            print(f"local UAV skip (missing): {src}")
            continue
        pairs = _iter_pairs(src)
        print(f"local {name}: pairs={len(pairs)}")
        for i, (img, lab) in enumerate(pairs):
            split = "val" if i % 8 == 0 else "train"
            stem = f"{name}_{img.stem}"
            img_dst = root / "images" / split / f"{stem}{img.suffix}"
            lab_dst = root / "labels" / split / f"{stem}.txt"
            if not img_dst.exists():
                shutil.copy2(img, img_dst)
            lines = []
            for line in lab.read_text(encoding="utf-8", errors="ignore").splitlines():
                parts = line.split()
                if len(parts) < 5:
                    continue
                parts[0] = str(CERBER_UAV)
                lines.append(" ".join(parts))
            lab_dst.parent.mkdir(parents=True, exist_ok=True)
            lab_dst.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
            if split == "train":
                tr += 1
            else:
                va += 1
    return tr, va


def print_manual_notes() -> None:
    print(
        """
=== MANUAL (not auto) ===
DUT Anti-UAV:  https://github.com/wangdongdut/DUT-Anti-UAV  (GDrive)
UETT4K:        https://github.com/mugheessarwarawan/UETT4K-Anti-UAV (SharePoint)
Drop YOLO under:
  $ROOT/sources/dut_anti_uav/
  $ROOT/sources/uett4k/
Then:  python prepare_data.py --root $ROOT --skip-visdrone --skip-seraphim --merge-local-uav
"""
    )


def main() -> int:
    p = argparse.ArgumentParser(description="CERBER V2 dataset prepare")
    p.add_argument(
        "--root",
        type=Path,
        default=Path(os.environ.get("CERBER_V2_ROOT", "/workspace/datasets/cerber_v2")),
    )
    p.add_argument("--skip-visdrone", action="store_true")
    p.add_argument("--skip-seraphim", action="store_true")
    p.add_argument("--skip-hf-extras", action="store_true")
    p.add_argument("--full-seraphim", action="store_true", help="Seraphim train/ ~9GB")
    p.add_argument("--merge-local-uav", action="store_true")
    p.add_argument("--hf-token", default=None)
    p.add_argument("--skip-download", action="store_true")
    args = p.parse_args()

    root = args.root
    token = args.hf_token or os.environ.get("HF_TOKEN")
    _ensure_splits(root)
    (root / "sources").mkdir(parents=True, exist_ok=True)

    print(f"CERBER V2 root={root}")
    print(f"PACK={PACK} REPO={REPO}")

    try:
        if not args.skip_visdrone:
            run_visdrone(root)
        if not args.skip_seraphim:
            run_seraphim(root, full=args.full_seraphim, token=token)
        if not args.skip_hf_extras:
            run_hf_extras(root, token=token, skip_dl=args.skip_download)
        if args.merge_local_uav:
            tr, va = merge_local_uav(root)
            print(f"local UAV merged train+={tr} val+={va}")
    except Exception as exc:  # noqa: BLE001
        print(f"BLOCKED: {exc}", file=sys.stderr)
        return 1

    _write_data_yaml(root)
    print_manual_notes()

    n_tr = len(list((root / "images" / "train").glob("*.*")))
    n_va = len(list((root / "images" / "val").glob("*.*")))
    print(f"READY images train={n_tr} val={n_va}")
    if n_tr < 100:
        print("BLOCKED: too few train images", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
