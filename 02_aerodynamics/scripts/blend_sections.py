#!/usr/bin/env python3
"""Blend MH61 → MH45 sections per BLEND.md; write station section CSVs.

Fails closed on bad Selig files or nonphysical thickness. No silent fallback
that collapses upper/lower surfaces.
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
AIR = ROOT / "airfoils"
GEOM = ROOT / "geometry"
OUT = AIR / "sections_blended"


def load_selig(path: Path) -> np.ndarray:
    if not path.is_file() or path.stat().st_size < 50:
        raise RuntimeError(f"BLOCKED: missing real airfoil {path}")
    lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    pts = []
    for line in lines:
        parts = line.replace(",", " ").split()
        if len(parts) < 2:
            continue
        try:
            x, y = float(parts[0]), float(parts[1])
        except ValueError:
            continue
        if 0.0 <= x <= 1.5 and abs(y) < 1.0:
            pts.append((x, y))
    arr = np.asarray(pts, dtype=float)
    if arr.size < 8:
        raise RuntimeError(f"BLOCKED: bad airfoil file: {path}")
    return arr


def surfaces_vs_x(coords: np.ndarray, n: int = 121) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return cosine-spaced x, y_upper, y_lower from a closed Selig loop."""
    i_le = int(np.argmin(coords[:, 0]))
    if coords[0, 0] < 0.2:
        upper = coords[: i_le + 1]
        lower = coords[i_le:]
    else:
        upper = coords[: i_le + 1][::-1]
        lower = coords[i_le:]

    def side_y(seg: np.ndarray, xq: np.ndarray) -> np.ndarray:
        order = np.argsort(seg[:, 0])
        x = np.clip(seg[order, 0], 0.0, 1.0)
        y = seg[order, 1]
        # unique x for interp
        _, uniq = np.unique(x, return_index=True)
        x_u, y_u = x[uniq], y[uniq]
        if len(x_u) < 4:
            raise RuntimeError("BLOCKED: airfoil surface has too few unique x stations")
        return np.interp(xq, x_u, y_u)

    beta = np.linspace(0.0, np.pi, n)
    xs = 0.5 * (1.0 - np.cos(beta))
    yu = side_y(upper, xs)
    yl = side_y(lower, xs)
    if np.any(yu < yl - 1e-6):
        # swap if winding inverted
        yu, yl = np.maximum(yu, yl), np.minimum(yu, yl)
    t_max = float(np.max(yu - yl))
    if t_max < 0.01:
        raise RuntimeError(f"BLOCKED: nonphysical max thickness t/c={t_max:.4f}")
    return xs, yu, yl


def blend(eta: float, a: tuple, b: tuple) -> tuple:
    xs, yu_a, yl_a = a
    _, yu_b, yl_b = b
    yu = (1 - eta) * yu_a + eta * yu_b
    yl = (1 - eta) * yl_a + eta * yl_b
    return xs, yu, yl


def scale_thickness(xs, yu, yl, t_c_target: float) -> tuple:
    t = yu - yl
    t_now = float(np.max(t))
    if t_now < 1e-6:
        raise RuntimeError("BLOCKED: cannot scale zero-thickness section")
    s = t_c_target / t_now
    mid = 0.5 * (yu + yl)
    return xs, mid + 0.5 * t * s, mid - 0.5 * t * s


def validate_section(xs, yu, yl) -> None:
    if len(xs) != len(yu) or len(xs) != len(yl):
        raise RuntimeError("BLOCKED: section length mismatch")
    if np.any(np.diff(xs) < -1e-12):
        raise RuntimeError("BLOCKED: section x not monotonic")
    if float(np.max(yu - yl)) < 0.01:
        raise RuntimeError("BLOCKED: section collapsed thickness")


def main() -> int:
    try:
        mh61 = surfaces_vs_x(load_selig(AIR / "mh61.dat"))
        mh45 = surfaces_vs_x(load_selig(AIR / "mh45.dat"))
        mh61_root = scale_thickness(*mh61, 0.15)
        validate_section(*mh61_root)
        validate_section(*mh45)

        stations_path = GEOM / "planform_stations.csv"
        if not stations_path.is_file():
            raise RuntimeError(f"BLOCKED: missing {stations_path}")

        OUT.mkdir(parents=True, exist_ok=True)
        with stations_path.open(encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        if not rows:
            raise RuntimeError("BLOCKED: empty planform_stations.csv")

        for row in rows:
            y = float(row["y_m"])
            chord = float(row["chord_m"])
            x_le = float(row["x_le_m"])
            if y <= 1.0:
                xs, yu, yl = mh61_root
                tag = "MH61_15pct"
            elif y >= 1.875:
                xs, yu, yl = mh45
                tag = "MH45"
            else:
                eta = (y - 1.0) / (1.875 - 1.0)
                xs, yu, yl = blend(eta, mh61_root, mh45)
                tag = f"blend_eta{eta:.2f}"
            validate_section(xs, yu, yl)

            out = OUT / f"section_y{y:.3f}.csv"
            with out.open("w", encoding="utf-8", newline="") as f:
                w = csv.writer(f)
                w.writerow(["x_m", "y_m", "z_upper_m", "z_lower_m", "airfoil"])
                for x_c, zu, zl in zip(xs, yu, yl):
                    w.writerow(
                        [
                            f"{x_le + x_c * chord:.6f}",
                            f"{y:.6f}",
                            f"{zu * chord:.6f}",
                            f"{zl * chord:.6f}",
                            tag,
                        ]
                    )
            print(out.name)
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
