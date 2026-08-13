#!/usr/bin/env python3
"""NULLXES BD Flight Sim S1 — product arcade. Not twin. Not ArduPlane.

  python run_sim.py
  python run_sim.py --cerber
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main() -> int:
    p = argparse.ArgumentParser(description="NULLXES BD-SIM S1")
    p.add_argument("--cerber", action="store_true", help="ZMQ to Studio worker (fail-closed)")
    args = p.parse_args()

    from PySide6.QtWidgets import QApplication

    from sim.app import SimWindow

    print("NULLXES BD-SIM S1 believable arcade · NOT TWIN · NOT ARDUPLANE")
    print("E=LAUNCH (no hover)  1 MANUAL  2 ASSIST  3 FOLLOW  4 MISSION")
    app = QApplication(sys.argv)
    app.setApplicationName("NULLXES BD-SIM")
    win = SimWindow(cerber=args.cerber)
    win.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
