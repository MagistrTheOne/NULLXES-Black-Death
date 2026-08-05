"""Export CERBER train curves for HW A/B compare (RTX 2080 vs RTX 6000)."""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib as mpl


def _load(csv_path: Path) -> dict[str, list[float]]:
    cols: dict[str, list[float]] = {}
    with csv_path.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            for k, v in row.items():
                cols.setdefault(k, []).append(float(v))
    return cols


def plot_run(
    csv_path: Path,
    out_dir: Path,
    *,
    label: str,
    gpu: str,
    imgsz: int,
    batch: int,
    train_n: int,
    val_n: int,
) -> Path:
    d = _load(csv_path)
    ep = d["epoch"]
    out_dir.mkdir(parents=True, exist_ok=True)

    # comparison-ready palette (not purple AI default)
    c_map = "#C45C26"
    c_map95 = "#1F4E5F"
    c_p = "#2E7D4F"
    c_r = "#8B3A3A"
    c_box = "#3D5A80"
    c_cls = "#E09F3E"
    c_dfl = "#9B2226"

    mpl.rcParams.update(
        {
            "figure.facecolor": "#0E1114",
            "axes.facecolor": "#151A1F",
            "axes.edgecolor": "#3A4550",
            "axes.labelcolor": "#D7DEE5",
            "xtick.color": "#A8B3BD",
            "ytick.color": "#A8B3BD",
            "text.color": "#E8EEF3",
            "grid.color": "#2A333C",
            "grid.linestyle": "--",
            "grid.linewidth": 0.6,
            "font.size": 10,
            "axes.titlesize": 12,
            "figure.titlesize": 14,
        }
    )

    fig, axes = plt.subplots(2, 2, figsize=(14, 9), constrained_layout=True)
    fig.suptitle(
        f"CERBER Detect FT — {label}\n"
        f"{gpu} · imgsz={imgsz} · batch={batch} · train={train_n} val={val_n} · epochs={int(ep[-1])}",
        fontweight="bold",
    )

    # mAP
    ax = axes[0, 0]
    ax.plot(ep, d["metrics/mAP50(B)"], color=c_map, lw=2.2, label="mAP50")
    ax.plot(ep, d["metrics/mAP50-95(B)"], color=c_map95, lw=2.0, label="mAP50-95")
    i50 = max(range(len(ep)), key=lambda i: d["metrics/mAP50(B)"][i])
    ax.scatter([ep[i50]], [d["metrics/mAP50(B)"][i50]], color=c_map, s=50, zorder=5)
    ax.annotate(
        f"best {d['metrics/mAP50(B)'][i50]:.4f} @ep{int(ep[i50])}",
        (ep[i50], d["metrics/mAP50(B)"][i50]),
        textcoords="offset points",
        xytext=(8, 8),
        color=c_map,
        fontsize=9,
    )
    ax.set_title("Validation mAP")
    ax.set_xlabel("epoch")
    ax.set_ylabel("score")
    ax.set_ylim(0.0, 1.0)
    ax.grid(True)
    ax.legend(frameon=False)

    # P / R
    ax = axes[0, 1]
    ax.plot(ep, d["metrics/precision(B)"], color=c_p, lw=2.0, label="precision")
    ax.plot(ep, d["metrics/recall(B)"], color=c_r, lw=2.0, label="recall")
    ax.set_title("Precision / Recall")
    ax.set_xlabel("epoch")
    ax.set_ylabel("score")
    ax.set_ylim(0.0, 1.0)
    ax.grid(True)
    ax.legend(frameon=False)

    # train loss
    ax = axes[1, 0]
    ax.plot(ep, d["train/box_loss"], color=c_box, lw=1.8, label="box")
    ax.plot(ep, d["train/cls_loss"], color=c_cls, lw=1.8, label="cls")
    ax.plot(ep, d["train/dfl_loss"], color=c_dfl, lw=1.8, label="dfl")
    ax.set_title("Train loss")
    ax.set_xlabel("epoch")
    ax.set_ylabel("loss")
    ax.grid(True)
    ax.legend(frameon=False)

    # val loss
    ax = axes[1, 1]
    ax.plot(ep, d["val/box_loss"], color=c_box, lw=1.8, label="box")
    ax.plot(ep, d["val/cls_loss"], color=c_cls, lw=1.8, label="cls")
    ax.plot(ep, d["val/dfl_loss"], color=c_dfl, lw=1.8, label="dfl")
    ax.set_title("Val loss")
    ax.set_xlabel("epoch")
    ax.set_ylabel("loss")
    ax.grid(True)
    ax.legend(frameon=False)

    png = out_dir / f"curves_{label.replace(' ', '_').lower()}.png"
    pdf = out_dir / f"curves_{label.replace(' ', '_').lower()}.pdf"
    fig.savefig(png, dpi=160)
    fig.savefig(pdf)
    plt.close(fig)

    # overlay-friendly single series CSV
    overlay = out_dir / "metrics_overlay.csv"
    with overlay.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(
            [
                "epoch",
                "mAP50",
                "mAP50_95",
                "precision",
                "recall",
                "train_box",
                "train_cls",
                "train_dfl",
                "val_box",
                "val_cls",
                "val_dfl",
                "time_s",
                "gpu",
                "label",
            ]
        )
        for i in range(len(ep)):
            w.writerow(
                [
                    int(ep[i]),
                    f"{d['metrics/mAP50(B)'][i]:.6f}",
                    f"{d['metrics/mAP50-95(B)'][i]:.6f}",
                    f"{d['metrics/precision(B)'][i]:.6f}",
                    f"{d['metrics/recall(B)'][i]:.6f}",
                    f"{d['train/box_loss'][i]:.6f}",
                    f"{d['train/cls_loss'][i]:.6f}",
                    f"{d['train/dfl_loss'][i]:.6f}",
                    f"{d['val/box_loss'][i]:.6f}",
                    f"{d['val/cls_loss'][i]:.6f}",
                    f"{d['val/dfl_loss'][i]:.6f}",
                    f"{d['time'][i]:.3f}",
                    gpu,
                    label,
                ]
            )

    meta = {
        "label": label,
        "gpu": gpu,
        "imgsz": imgsz,
        "batch": batch,
        "train_images": train_n,
        "val_images": val_n,
        "epochs": int(ep[-1]),
        "wall_time_min": round(d["time"][-1] / 60.0, 2),
        "best_mAP50": round(d["metrics/mAP50(B)"][i50], 4),
        "best_mAP50_epoch": int(ep[i50]),
        "last_mAP50": round(d["metrics/mAP50(B)"][-1], 4),
        "best_mAP50_95": round(max(d["metrics/mAP50-95(B)"]), 4),
        "best_precision": round(max(d["metrics/precision(B)"]), 4),
        "best_recall": round(max(d["metrics/recall(B)"]), 4),
        "dataset": "VisDrone-only (Seraphim skipped)",
        "run_name": "v2-pursuit-2080",
        "source_csv": str(csv_path.resolve()),
        "exports": {
            "png": str(png.resolve()),
            "pdf": str(pdf.resolve()),
            "overlay_csv": str(overlay.resolve()),
        },
    }
    (out_dir / "run_meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    # copy raw ultralytics csv
    raw_dst = out_dir / "results_raw.csv"
    raw_dst.write_text(csv_path.read_text(encoding="utf-8"), encoding="utf-8")
    print(json.dumps(meta, indent=2))
    return png


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--csv", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--label", default="rtx2080_super")
    p.add_argument("--gpu", default="NVIDIA GeForce RTX 2080 SUPER 8GB")
    p.add_argument("--imgsz", type=int, default=640)
    p.add_argument("--batch", type=int, default=6)
    p.add_argument("--train-n", type=int, default=6471)
    p.add_argument("--val-n", type=int, default=548)
    a = p.parse_args()
    plot_run(
        a.csv,
        a.out,
        label=a.label,
        gpu=a.gpu,
        imgsz=a.imgsz,
        batch=a.batch,
        train_n=a.train_n,
        val_n=a.val_n,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
