#!/usr/bin/env python3
"""Run XFOIL polars for MH45/MH61 → CSV under airfoils/polars/.

Requires `xfoil` on PATH and real `mh45.dat` / `mh61.dat`.
No analytic fallback — missing XFOIL → BLOCKED (exit 1).
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AIRFOILS = ROOT / "airfoils"
OUT = AIRFOILS / "polars"
RE_LIST = [1.0e6, 3.0e6, 7.0e6]
ALPHA_MIN, ALPHA_MAX, ALPHA_STEP = -4.0, 12.0, 1.0
FOILS = ("mh45", "mh61")


def write_csv(path: Path, rows: list[tuple[float, float, float, float]], meta: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"# {meta}", "alpha_deg,cl,cd,cm"]
    for a, cl, cd, cm in rows:
        lines.append(f"{a:.3f},{cl:.6f},{cd:.6f},{cm:.6f}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_xfoil(foil: str, re: float) -> list[tuple[float, float, float, float]]:
    if not shutil.which("xfoil"):
        raise RuntimeError("BLOCKED: xfoil not on PATH")
    dat = AIRFOILS / f"{foil}.dat"
    if not dat.is_file() or dat.stat().st_size < 50:
        raise RuntimeError(f"BLOCKED: missing real airfoil {dat}")
    with tempfile.TemporaryDirectory() as td:
        tdir = Path(td)
        polar = tdir / "polar.txt"
        script = f"""
LOAD {dat.as_posix()}
PANE
OPER
VISC {re:.0f}
PACC
{polar.as_posix()}

ASEQ {ALPHA_MIN} {ALPHA_MAX} {ALPHA_STEP}
PACC
QUIT
"""
        try:
            subprocess.run(
                ["xfoil"],
                input=script,
                text=True,
                capture_output=True,
                timeout=120,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise RuntimeError(f"BLOCKED: xfoil failed for {foil} Re={re}: {exc}") from exc
        if not polar.exists():
            raise RuntimeError(f"BLOCKED: xfoil produced no polar for {foil} Re={re}")
        rows: list[tuple[float, float, float, float]] = []
        for line in polar.read_text(encoding="utf-8", errors="ignore").splitlines():
            parts = line.split()
            if len(parts) < 4:
                continue
            try:
                a, cl, cd, cm = map(float, parts[:4])
            except ValueError:
                continue
            rows.append((a, cl, cd, cm))
        if not rows:
            raise RuntimeError(f"BLOCKED: empty polar parse for {foil} Re={re}")
        return rows


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    try:
        for foil in FOILS:
            for re in RE_LIST:
                tag = f"{foil}_Re{re:.0e}".replace("+", "")
                path = OUT / f"{tag}.csv"
                rows = run_xfoil(foil, re)
                write_csv(path, rows, f"XFOIL {foil} Re={re:.0e}")
                print(f"XFOIL {path.name}")
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
