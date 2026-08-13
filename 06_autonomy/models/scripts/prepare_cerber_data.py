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
import os
import shutil
import sys
from pathlib import Path

import yaml

os.environ.setdefault("YOLO_AUTOINSTALL", "false")
_REPO = Path(__file__).resolve().parents[3]
_ASSETS = "https://github.com/ultralytics/assets/releases/download/v0.0.0"

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

# UETT4K is NOT on Hugging Face. Full dump is SharePoint (from GitHub README).
# GitHub only hosts paper/sample refs — not the 33k YOLO tree.
UETT4K_GITHUB = "https://github.com/mugheessarwarawan/UETT4K-Anti-UAV"
UETT4K_SHAREPOINT = (
    "https://pern-my.sharepoint.com/:f:/g/personal/mughees_sarwar_ist_edu_pk/"
    "EnIRYWzXcZZBkOUUn0Ltb-4BiXzC6SQpZvIlGbnsFqQKaA?e=M2SULN"
)
# Optional HF substitute for class uav=2 (YOLO, downloadable):
HF_UAV_YOLO = "lgrzybowski/seraphim-drone-detection-dataset"
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


def _count_jpg(d: Path) -> int:
    if not d.is_dir():
        return 0
    return sum(1 for _ in d.glob("*.jpg"))


def _visdrone_dir() -> Path:
    env = os.environ.get("VISDRONE_DIR")
    if env:
        p = Path(env)
        if _count_jpg(p / "images" / "train") >= 1000 or (p / "VisDrone2019-DET-train").is_dir():
            return p
    for c in (
        _REPO / "datasets" / "VisDrone",
        Path("/workspace/datasets/VisDrone"),
    ):
        if _count_jpg(c / "images" / "train") >= 1000 or (c / "VisDrone2019-DET-train").is_dir():
            return c
    if Path("/workspace/datasets").is_dir():
        return Path("/workspace/datasets/VisDrone")
    return _REPO / "datasets" / "VisDrone"


def _visdrone2yolo(vd: Path, split: str, source_name: str) -> int:
    """VisDrone CSV → YOLO. Skip annotation files whose jpg is missing (upstream zip holes)."""
    from PIL import Image

    source_dir = vd / source_name
    images_dir = vd / "images" / split
    labels_dir = vd / "labels" / split
    labels_dir.mkdir(parents=True, exist_ok=True)
    src_images = source_dir / "images"
    if src_images.is_dir():
        images_dir.mkdir(parents=True, exist_ok=True)
        for img in src_images.glob("*.jpg"):
            dest = images_dir / img.name
            if not dest.exists():
                img.rename(dest)
    ann_dir = source_dir / "annotations"
    if not ann_dir.is_dir():
        n_lbl = sum(1 for _ in labels_dir.glob("*.txt")) if labels_dir.is_dir() else 0
        print(f"VisDrone {split}: annotations gone, labels already={n_lbl}")
        return 0
    skipped = 0
    converted = 0
    for f in sorted(ann_dir.glob("*.txt")):
        img_path = images_dir / f.with_suffix(".jpg").name
        if not img_path.is_file():
            skipped += 1
            continue
        with Image.open(img_path) as im:
            w, h = im.size
        dw, dh = 1.0 / float(w), 1.0 / float(h)
        lines: list[str] = []
        for raw in f.read_text(encoding="utf-8", errors="ignore").strip().splitlines():
            row = raw.split(",")
            if len(row) < 6 or row[4] == "0":
                continue
            x, y, bw, bh = map(int, row[:4])
            cls = int(row[5]) - 1
            lines.append(
                f"{cls} {(x + bw / 2) * dw:.6f} {(y + bh / 2) * dh:.6f} {bw * dw:.6f} {bh * dh:.6f}"
            )
        (labels_dir / f.name).write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
        converted += 1
    print(f"VisDrone {split}: yolo={converted} skipped_missing_jpg={skipped}")
    return skipped


def fetch_visdrone(root: Path) -> Path:
    """Download VisDrone zips, convert (skip missing jpg), remap into CERBER tree."""
    vd_root = _visdrone_dir()
    vd_root.mkdir(parents=True, exist_ok=True)
    print(f"VisDrone docs: {VISDRONE_DOCS}")
    print(f"VisDrone at {vd_root}")

    n_train = _count_jpg(vd_root / "images" / "train")
    src_train = vd_root / "VisDrone2019-DET-train" / "images"
    need_dl = n_train < 1000 and _count_jpg(src_train) < 1000
    if need_dl:
        try:
            from ultralytics.utils.downloads import download
        except ImportError as exc:
            raise RuntimeError("BLOCKED: ultralytics required. pip install -U ultralytics") from exc
        urls = [
            f"{_ASSETS}/VisDrone2019-DET-train.zip",
            f"{_ASSETS}/VisDrone2019-DET-val.zip",
        ]
        print("Downloading VisDrone zips (~2GB)...")
        download(urls, dir=vd_root, threads=2)
    else:
        print(f"VisDrone images already present train_jpg={n_train}")

    splits = {
        "VisDrone2019-DET-train": "train",
        "VisDrone2019-DET-val": "val",
    }
    for folder, split in splits.items():
        _visdrone2yolo(vd_root, split, folder)
        leftover = vd_root / folder
        if leftover.is_dir() and _count_jpg(leftover / "images") == 0:
            shutil.rmtree(leftover, ignore_errors=True)

    for split in ("train", "val"):
        img_src = vd_root / "images" / split
        lbl_src = vd_root / "labels" / split
        if not img_src.is_dir():
            print(f"BLOCKED: VisDrone split missing {split} under {vd_root}")
            continue
        img_dst = root / "images" / split
        lbl_dst = root / "labels" / split
        img_dst.mkdir(parents=True, exist_ok=True)
        lbl_dst.mkdir(parents=True, exist_ok=True)
        n = 0
        for img in img_src.glob("*.*"):
            if img.suffix.lower() not in {".jpg", ".jpeg", ".png"}:
                continue
            target = img_dst / f"vd_{img.name}"
            if not target.exists():
                shutil.copy2(img, target)
            lab = lbl_src / f"{img.stem}.txt"
            if lab.is_file():
                _remap_label_file(lab, lbl_dst / f"vd_{img.stem}.txt", _VISDRONE_TO_CERBER)
            n += 1
        print(f"CERBER merge VisDrone {split}={n}")
    return vd_root


def write_uett4k_download_note(root: Path) -> Path:
    """UETT4K full set is SharePoint-only; GitHub has no bulk YOLO dump."""
    dest = root / "sources" / "uett4k"
    dest.mkdir(parents=True, exist_ok=True)
    note = dest / "DOWNLOAD.txt"
    note.write_text(
        "UETT4K Anti-UAV (~33601 imgs) is NOT in git LFS / HF.\n"
        f"GitHub (readme + link): {UETT4K_GITHUB}\n"
        f"Full dataset (SharePoint): {UETT4K_SHAREPOINT}\n"
        "Download zips in browser / rclone, unpack YOLO tree, map class → CERBER id=2 (uav),\n"
        "copy into ../../images/{{train,val}} + ../../labels/{{train,val}}.\n"
        f"Optional auto HF UAV YOLO: {HF_UAV_YOLO}\n",
        encoding="utf-8",
    )
    print(f"UETT4K: not on GitHub as data — see {note}")
    print(f"  SharePoint: {UETT4K_SHAREPOINT}")
    return dest


def fetch_hf_uav_yolo(root: Path, token: str | None) -> Path:
    """Optional downloadable UAV detector set (Seraphim) → CERBER class uav=2."""
    try:
        from huggingface_hub import snapshot_download
    except ImportError as exc:
        raise RuntimeError(
            "BLOCKED: huggingface_hub required. pip install huggingface_hub"
        ) from exc

    dest = root / "sources" / "seraphim_uav"
    dest.mkdir(parents=True, exist_ok=True)
    print(f"HF snapshot: {HF_UAV_YOLO} → {dest}")
    path = snapshot_download(
        repo_id=HF_UAV_YOLO,
        repo_type="dataset",
        local_dir=str(dest),
        token=token,
    )
    (dest / "CERBER_IMPORT.txt").write_text(
        "Seraphim drone YOLO (class 0). Remap to CERBER id=2 (uav) and merge "
        "into images/{train,val} + labels/{train,val}.\n"
        f"Hub: https://huggingface.co/datasets/{HF_UAV_YOLO}\n",
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
| UETT4K (SharePoint via GitHub README) | {UETT4K_SHAREPOINT} |
| UAV YOLO alt (HF Seraphim) | https://huggingface.co/datasets/{HF_UAV_YOLO} |

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
    p.add_argument("--skip-hf", action="store_true", help="skip optional Seraphim UAV HF")
    p.add_argument(
        "--fetch-uav-hf",
        action="store_true",
        help=f"download {HF_UAV_YOLO} (UETT4K is SharePoint-only)",
    )
    p.add_argument("--hf-token", default=None, help="HF token or set HF_TOKEN env")
    args = p.parse_args()

    root: Path = args.root
    (root / "images" / "train").mkdir(parents=True, exist_ok=True)
    (root / "images" / "val").mkdir(parents=True, exist_ok=True)
    (root / "labels" / "train").mkdir(parents=True, exist_ok=True)
    (root / "labels" / "val").mkdir(parents=True, exist_ok=True)

    print_manual_sources(root)
    write_uett4k_download_note(root)
    data_yaml = _write_data_yaml(root, template)
    print(f"data.yaml → {data_yaml}")

    try:
        if not args.skip_visdrone:
            fetch_visdrone(root)
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    if args.fetch_uav_hf and not args.skip_hf:
        import os

        token = args.hf_token or os.environ.get("HF_TOKEN")
        try:
            fetch_hf_uav_yolo(root, token)
        except Exception as exc:  # noqa: BLE001
            print(f"HF UAV YOLO: {exc}", file=sys.stderr)

    print("OK — next: python models/scripts/train_cerber_detect.py --data", data_yaml)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
