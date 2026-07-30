"""Dual-compute entry — SoftBus heartbeat pulse (wall clock only)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from ros2.nodes._spin import spin_pulse
from ros2.nodes.dual_soft import DualSoftNode
from soft_bus.bus import SoftBus


def main() -> None:
    bus = SoftBus()
    node = DualSoftNode(bus, channel_id="A")
    spin_pulse("dual_entry", node.pulse, period_s=0.1)


if __name__ == "__main__":
    main()
