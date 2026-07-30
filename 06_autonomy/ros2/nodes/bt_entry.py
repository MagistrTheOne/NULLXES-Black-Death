"""BT/FM entry — SoftBus; waits for real health topics."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from ros2.nodes._spin import spin_idle
from ros2.nodes.fm_bt_soft import main as soft_main


def main() -> None:
    soft_main()
    spin_idle("bt_entry")


if __name__ == "__main__":
    main()
