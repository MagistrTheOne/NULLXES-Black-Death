"""SoftBus entry helpers — attach algorithms; spin until KeyboardInterrupt.

Does not invent sensor data. Dual pulses real wall-clock heartbeats only.
"""

from __future__ import annotations

import time
from typing import Callable


def spin_idle(label: str) -> None:
    print(f"{label}: attached; waiting for bus traffic (Ctrl+C to exit)")
    try:
        while True:
            time.sleep(1.0)
    except KeyboardInterrupt:
        print(f"{label}: stop")


def spin_pulse(label: str, pulse: Callable[[], None], period_s: float = 0.1) -> None:
    print(f"{label}: pulsing heartbeat @ {1.0 / period_s:.0f} Hz (Ctrl+C to exit)")
    try:
        while True:
            pulse()
            time.sleep(period_s)
    except KeyboardInterrupt:
        print(f"{label}: stop")
