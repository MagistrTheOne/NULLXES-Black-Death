"""Guidance entry — SoftBus; waits for real NAV+GOAL."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from ros2.nodes._spin import spin_idle
from ros2.nodes.guidance_soft import main as soft_main


def main() -> None:
    soft_main()
    spin_idle("guidance_entry")


if __name__ == "__main__":
    main()
