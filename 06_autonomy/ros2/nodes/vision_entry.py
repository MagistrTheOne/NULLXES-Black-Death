"""Vision entry — SoftBus node; BLOCKED without real ONNX + camera topics."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from ros2.nodes._spin import spin_idle
from ros2.nodes.vision_soft import BlockedError, main as soft_main


def main() -> None:
    try:
        soft_main()
    except BlockedError as exc:
        print(exc)
        raise SystemExit(2) from exc
    spin_idle("vision_entry")


if __name__ == "__main__":
    main()
