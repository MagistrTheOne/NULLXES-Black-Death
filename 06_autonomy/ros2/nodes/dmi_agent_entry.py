"""DMI agent entry — onboard SoftBus node; pulses agent status."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from ros2.nodes._spin import spin_pulse
from ros2.nodes.dmi_agent_soft import DmiAgentSoftNode
from soft_bus.bus import SoftBus


def main() -> None:
    bus = SoftBus()
    node = DmiAgentSoftNode(bus, agent_id="bj-1")
    spin_pulse("dmi_agent_entry", node.publish_status, period_s=0.5)


if __name__ == "__main__":
    main()
