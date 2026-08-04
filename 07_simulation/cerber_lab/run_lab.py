#!/usr/bin/env python3
"""NULLXES CERBER Lab — entrypoint.

  python run_lab.py
  python run_lab.py --wing s800
  python run_lab.py --wing ar_wing --cerber
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main() -> int:
    p = argparse.ArgumentParser(description="NULLXES CERBER Lab (arcade viz)")
    p.add_argument(
        "--wing",
        choices=("s800", "ar_wing"),
        default="ar_wing",
        help="visual airframe preset",
    )
    p.add_argument(
        "--cerber",
        action="store_true",
        help="load real CERBER ONNX overlay (fail-closed if missing)",
    )
    args = p.parse_args()
    from lab.app import run_lab

    print("NULLXES CERBER Lab · ARCADE VIZ · NOT DIGITAL TWIN")
    print(f"wing={args.wing} cerber={args.cerber}")
    run_lab(wing=args.wing, cerber=args.cerber)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
