#!/usr/bin/env python3
"""ALPHA 5x5 planform generator — locked b=5 m, S=20 m^2."""

from __future__ import annotations

import csv
import math
from pathlib import Path

# --- locked baseline geometry ---
SPAN_M = 5.0
AREA_M2 = 20.0
ROOT_CHORD_M = 5.0
TIP_CHORD_M = 3.0  # (cr+ct)/2*b = 20
LE_SWEEP_DEG = 22.5
N_STATIONS = 5  # including root and tip

OUT = Path(__file__).resolve().parent


def chord_at(y: float) -> float:
    """Linear taper, y from 0..b/2."""
    eta = y / (SPAN_M / 2.0)
    return ROOT_CHORD_M + eta * (TIP_CHORD_M - ROOT_CHORD_M)


def le_x(y: float) -> float:
    return y * math.tan(math.radians(LE_SWEEP_DEG))


def stations():
    ys = [i * (SPAN_M / 2.0) / (N_STATIONS - 1) for i in range(N_STATIONS)]
    rows = []
    for y in ys:
        c = chord_at(y)
        x_le = le_x(y)
        rows.append(
            {
                "y_m": round(y, 6),
                "chord_m": round(c, 6),
                "x_le_m": round(x_le, 6),
                "x_te_m": round(x_le + c, 6),
            }
        )
    return rows


def outline(rows):
    """Closed planform polygon: nose -> LE right -> TE right -> TE CL -> TE left -> LE left -> nose."""
    right = rows
    pts = []
    # LE root -> LE tip (right)
    for r in right:
        pts.append((r["x_le_m"], r["y_m"]))
    # TE tip -> TE root (right)
    for r in reversed(right):
        pts.append((r["x_te_m"], r["y_m"]))
    # TE root -> TE tip (left), skip duplicate TE root
    for r in right[1:]:
        pts.append((r["x_te_m"], -r["y_m"]))
    # LE tip -> LE root (left), skip tip duplicate if any
    for r in reversed(right[1:]):
        pts.append((r["x_le_m"], -r["y_m"]))
    pts.append(pts[0])
    return pts


def area_check(rows) -> float:
    # trapezoid formula
    return (ROOT_CHORD_M + TIP_CHORD_M) / 2.0 * SPAN_M


def te_sweep_deg() -> float:
    """TE sweep from tip TE relative to root TE."""
    y_t = SPAN_M / 2.0
    x_te_root = ROOT_CHORD_M
    x_te_tip = le_x(y_t) + TIP_CHORD_M
    return math.degrees(math.atan2(x_te_tip - x_te_root, y_t))


def main() -> None:
    rows = stations()
    assert abs(area_check(rows) - AREA_M2) < 1e-9

    stations_path = OUT / "planform_stations.csv"
    with stations_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["y_m", "chord_m", "x_le_m", "x_te_m"])
        w.writeheader()
        w.writerows(rows)

    outline_path = OUT / "planform_outline.csv"
    with outline_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["x_m", "y_m", "z_m"])
        for x, y in outline(rows):
            w.writerow([f"{x:.6f}", f"{y:.6f}", "0.000000"])

    print(f"S_check={area_check(rows):.4f} m^2")
    print(f"AR={SPAN_M**2 / AREA_M2:.4f}")
    print(f"Lambda_TE≈{te_sweep_deg():.2f} deg")
    print(f"wrote {stations_path.name}, {outline_path.name}")


if __name__ == "__main__":
    main()
