#!/usr/bin/env python3
"""Export front/rear spar station XYZ from planform CSV."""

from __future__ import annotations

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GEOM = ROOT.parent / "02_aerodynamics" / "geometry" / "planform_stations.csv"
OUT = ROOT / "load_paths" / "spar_stations.csv"
FRONT_C = 0.25
REAR_C = 0.65


def main() -> None:
    rows_out = []
    with GEOM.open(encoding="utf-8") as f:
        for r in csv.DictReader(f):
            y = float(r["y_m"])
            c = float(r["chord_m"])
            x_le = float(r["x_le_m"])
            for side in (1.0, -1.0):
                if y == 0.0 and side < 0:
                    continue
                yy = side * y
                rows_out.append(
                    {
                        "y_m": f"{yy:.6f}",
                        "x_front_m": f"{x_le + FRONT_C * c:.6f}",
                        "x_rear_m": f"{x_le + REAR_C * c:.6f}",
                        "chord_m": f"{c:.6f}",
                    }
                )
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["y_m", "x_front_m", "x_rear_m", "chord_m"])
        w.writeheader()
        w.writerows(rows_out)
    print(f"wrote {OUT} ({len(rows_out)} rows)")


if __name__ == "__main__":
    main()
