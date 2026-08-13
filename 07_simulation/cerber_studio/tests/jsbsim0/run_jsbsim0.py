"""JSBSIM-0 — headless initialize / controls / step / state / reset / shutdown."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from studio.sim.environment import PhysicalAtmosphere
from studio.sim.jsbsim0 import JSBSim0
from studio.sim.vehicle import ControlInput


def run() -> dict:
    fdm = JSBSim0()
    kind = fdm.initialize()
    fdm.set_controls(ControlInput(pitch=0.1, roll=0.05, yaw=0.0, throttle=0.7))
    last = None
    for _ in range(200):
        last = fdm.step(0.01, PhysicalAtmosphere(1.0, 0.2, 288.15, 101325.0, 1.225))
    assert last is not None
    assert all(abs(x) < 1e9 for x in last.position)
    east, north, up = last.position
    fdm.reset()
    after = fdm.vehicle_state()
    fdm.shutdown()
    return {
        "kind": kind,
        "jsbsim_package": fdm.available,
        "steps": 200,
        "final_enu_m": {"east": east, "north": north, "up": up},
        "airspeed": last.airspeed,
        "heading": last.heading,
        "reset_timestamp": after.timestamp,
        "shutdown": True,
    }


if __name__ == "__main__":
    import yaml

    print(yaml.safe_dump(run(), allow_unicode=True, sort_keys=False))
