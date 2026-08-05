"""Overlay two CERBER train exports (e.g. RTX 2080 vs RTX 6000)."""
from __future__ import annotations

import argparse
import csv
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib as mpl


def _load(path: Path) -> dict[str, list[float | str]]:
    cols: dict[str, list] = {}
    with path.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            for k, v in row.items():
                if k in ("gpu", "label"):
                    cols.setdefault(k, []).append(v)
                else:
                    cols.setdefault(k, []).append(float(v))
    return cols


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--a", type=Path, required=True, help="metrics_overlay.csv run A")
    p.add_argument("--b", type=Path, required=True, help="metrics_overlay.csv run B")
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()

    a = _load(args.a)
    b = _load(args.b)
    la = str(a["label"][0])
    lb = str(b["label"][0])

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
            "font.size": 10,
        }
    )

    fig, axes = plt.subplots(1, 2, figsize=(14, 5.5), constrained_layout=True)
    fig.suptitle(f"CERBER Detect A/B — {la} vs {lb}", fontweight="bold")

    ax = axes[0]
    ax.plot(a["epoch"], a["mAP50"], color="#C45C26", lw=2.2, label=f"{la} mAP50")
    ax.plot(b["epoch"], b["mAP50"], color="#4CC9F0", lw=2.2, label=f"{lb} mAP50")
    ax.plot(a["epoch"], a["mAP50_95"], color="#C45C26", lw=1.4, ls="--", alpha=0.85, label=f"{la} mAP50-95")
    ax.plot(b["epoch"], b["mAP50_95"], color="#4CC9F0", lw=1.4, ls="--", alpha=0.85, label=f"{lb} mAP50-95")
    ax.set_title("mAP")
    ax.set_xlabel("epoch")
    ax.set_ylim(0, 1)
    ax.grid(True)
    ax.legend(frameon=False, fontsize=8)

    ax = axes[1]
    ax.plot(a["epoch"], a["precision"], color="#C45C26", lw=2.0, label=f"{la} P")
    ax.plot(b["epoch"], b["precision"], color="#4CC9F0", lw=2.0, label=f"{lb} P")
    ax.plot(a["epoch"], a["recall"], color="#C45C26", lw=1.4, ls="--", label=f"{la} R")
    ax.plot(b["epoch"], b["recall"], color="#4CC9F0", lw=1.4, ls="--", label=f"{lb} R")
    ax.set_title("Precision / Recall")
    ax.set_xlabel("epoch")
    ax.set_ylim(0, 1)
    ax.grid(True)
    ax.legend(frameon=False, fontsize=8)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.out, dpi=160)
    fig.savefig(args.out.with_suffix(".pdf"))
    plt.close(fig)
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
