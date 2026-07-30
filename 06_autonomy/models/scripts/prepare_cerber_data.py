#!/usr/bin/env python3
"""Bootstrap CERBER detect datasets on the train host.

Sources:
  - VisDrone via Ultralytics auto-download (https://docs.ultralytics.com/datasets/detect/visdrone)
  - UETT4k-Anti-UAV via Hugging Face hub (mugheessarwarawan/UETT4k-Anti-UAV)
  - UAVDT / DOTA: print DatasetNinja URLs — place YOLO dirs under sources/ when ready

Usage:
  python prepare_cerber_data.py --root /data/nullxes/datasets/cerber
  python prepare_cerber_data.py --root /data/nullxes/datasets/cerber --skip-visdrone
  python prepare_cerber_data.py --root /data/nullxes/datasets/cerber --hf-token $HF_TOKEN
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

import yaml

# VisDrone class id → CERBER id (human=0, vehicle=1)
_VISDRONE_TO_CERBER = {
    0: 0,  # pedestrian
    1: 0,  # people
    2: 1,  # bicycle
    3: 1,  # car
    4: 1,  # van
    5: 1,  # truck
    6: 1,  # tricycle
    7: 1,  # awning-tricycle
    8: 1,  # bus
    9: 1,  # motor
}

HF_UETT4K = "mugheessarwarawan/UETT4k-Anti-UAV"
UAVDT_URL = "https://datasetninja.com/uavdt"
DOTA_URL = "https://datasetninja.com/dota"
VISDRONE_DOCS = "https://docs.ultralytics.com/datasets/detect/visdrone"


def _write_data_yaml(root: Path, repo_template: Path) -> Path:
    out = root / "data.yaml"
    cfg = yaml.safe_load(repo_template.read_text(encoding="utf-8"))
    cfg["path"] = str(root.resolve())
    out.write_text(yaml.safe_dump(cfg, sort_keys=False), encoding="utf-8")
    return out


def _remap_label_file(src: Path, dst: Path, mapping: dict[int, int]) -> None:
    lines_out: list[str] = []
    for line in src.read_text(encoding="utf-8").splitlines():
        parts = line.split()
        if len(parts) < 5:
            continue
        cls = int(float(parts[0]))
        if cls not in mapping:
            continue
        parts[0] = str(mapping[cls])
        lines_out.append(" ".join(parts))
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text("\n".join(lines_out) + ("\n" if lines_out else ""), encoding="utf-8")


def fetch_visdrone(root: Path) -> Path:
    """Trigger Ultralytics VisDrone download+convert, then remap into CERBER tree."""
    try:
        from ultralytics.data.utils import check_det_dataset
    except ImportError as exc:
        raise RuntimeError(
            "BLOCKED: ultralytics required. pip install -U ultralytics"
        ) from exc

    print(f"VisDrone docs: {VISDRONE_DOCS}")
    print("Downloading / converting VisDrone via Ultralytics (first run ~2GB)...")
    data = check_det_dataset("VisDrone.yaml")
    vd_root = Path(data["path"])
    print(f"VisDrone at {vd_root}")

    for split in ("train", "val"):
        img_src = vd_root / "images" / split
        lbl_src = vd_root / "labels" / split
        if not img_src.is_dir() or not lbl_src.is_dir():
            print(f"BLOCKED: VisDrone split missing {split} under {vd_root}")
            continue
        img_dst = root / "images" / split
        lbl_dst = root / "labels" / split
        img_dst.mkdir(parents=True, exist_ok=True)
        lbl_dst.mkdir(parents=True, exist_ok=True)
        for img in img_src.glob("*.*"):
            target = img_dst / f"vd_{img.name}"
            if not target.exists():
                shutil.copy2(img, target)
            lab = lbl_src / f"{img.stem}.txt"
            if lab.is_file():
                _remap_label_file(lab, lbl_dst / f"vd_{img.stem}.txt", _VISDRONE_TO_CERBER)
    return vd_root


def fetch_hf_uett4k(root: Path, token: str | None) -> Path:
    try:
        from huggingface_hub import snapshot_download
    except ImportError as exc:
        raise RuntimeError(
            "BLOCKED: huggingface_hub required. pip install huggingface_hub"
        ) from exc

    dest = root / "sources" / "uett4k"
    dest.mkdir(parents=True, exist_ok=True)
    print(f"HF snapshot: {HF_UETT4K} → {dest}")
    path = snapshot_download(
        repo_id=HF_UETT4K,
        repo_type="dataset",
        local_dir=str(dest),
        token=token,
    )
    readme = dest / "CERBER_IMPORT.txt"
    readme.write_text(
        "UETT4k downloaded. Convert annotations to YOLO CERBER id=2 (uav) "
        "and copy into images/{train,val} + labels/{train,val} before full train.\n"
        f"Hub: https://huggingface.co/datasets/{HF_UETT4K}\n",
        encoding="utf-8",
    )
    return Path(path)


def print_manual_sources(root: Path) -> None:
    man = root / "sources" / "MANUAL_DOWNLOADS.md"
    man.parent.mkdir(parents=True, exist_ok=True)
    man.write_text(
        f"""# Manual CERBER sources

Place converted YOLO trees here, then merge into `../images` + `../labels`.

| Dataset | Link |
|---------|------|
| UAVDT | {UAVDT_URL} |
| DOTA | {DOTA_URL} |
| VisDrone (docs) | {VISDRONE_DOCS} |
| UETT4k (HF) | https://huggingface.co/datasets/{HF_UETT4K} |

Remap rules: `06_autonomy/models/datasets/remap_rules.yaml`
""",
        encoding="utf-8",
    )
    print(f"Wrote {man}")


def main() -> int:
    repo = Path(__file__).resolve().parents[3]
    template = repo / "06_autonomy" / "models" / "datasets" / "cerber_data.yaml"

    p = argparse.ArgumentParser(description="Prepare CERBER detect dataset root")
    p.add_argument(
        "--root",
        type=Path,
        default=Path("/data/nullxes/datasets/cerber"),
        help="dataset root (images/, labels/, data.yaml)",
    )
    p.add_argument("--skip-visdrone", action="store_true")
    p.add_argument("--skip-hf", action="store_true")
    p.add_argument("--hf-token", default=None, help="HF token or set HF_TOKEN env")
    args = p.parse_args()

    root: Path = args.root
    (root / "images" / "train").mkdir(parents=True, exist_ok=True)
    (root / "images" / "val").mkdir(parents=True, exist_ok=True)
    (root / "labels" / "train").mkdir(parents=True, exist_ok=True)
    (root / "labels" / "val").mkdir(parents=True, exist_ok=True)

    print_manual_sources(root)
    data_yaml = _write_data_yaml(root, template)
    print(f"data.yaml → {data_yaml}")

    try:
        if not args.skip_visdrone:
            fetch_visdrone(root)
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    if not args.skip_hf:
        import os

        token = args.hf_token or os.environ.get("HF_TOKEN")
        try:
            fetch_hf_uett4k(root, token)
        except Exception as exc:  # noqa: BLE001 — surface HF auth/network clearly
            print(f"HF UETT4k: {exc}", file=sys.stderr)
            print(
                "Continue without HF or: huggingface-cli login / --hf-token",
                file=sys.stderr,
            )

    print("OK — next: python models/scripts/train_cerber_detect.py --data", data_yaml)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
