"""Headless validation stills for STABILIZATION PASS 01."""

from __future__ import annotations

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from studio.config.paths import user_dir
from studio.config.settings import UserSettings
from studio.viewport import StudioEngine
from studio.aircraft.registry import AircraftRegistry


def _step(eng: StudioEngine, n: int = 8) -> None:
    for _ in range(n):
        eng.step_world()


def main() -> None:
    out = user_dir() / "validation"
    out.mkdir(parents=True, exist_ok=True)
    settings = UserSettings()
    eng = StudioEngine(width=1280, height=720, settings=settings)
    eng.debug_perf = True
    eng.profiler.enabled = True
    reg = AircraftRegistry()
    items = reg.scan()
    if items:
        eng.apply_definition(items[0])
    eng.set_scene_mode("hangar")
    _step(eng, 12)
    eng.screenshot_to(out / "03_hangar_animated_drone.png")
    if len(items) > 1:
        eng.apply_definition(items[1])
        _step(eng, 8)
        eng.screenshot_to(out / "04_hangar_second.png")
    eng.preview_region("arctic")
    _step(eng, 10)
    eng.screenshot_to(out / "01_region_arctic.png")
    eng.preview_region("coast")
    _step(eng, 10)
    eng.screenshot_to(out / "02_region_coast.png")
    eng.set_scene_mode("flight")
    sess = settings.session
    sess.region_id = "arctic"
    sess.world_seed = 1947
    eng.prepare_world()
    eng.spawn_ready()
    _step(eng, 16)
    eng.screenshot_to(out / "05_flight_ground.png")
    st = eng.dynamics.state
    st.z = float(st.z) + 90.0
    _step(eng, 12)
    eng.screenshot_to(out / "06_flight_airborne.png")
    eng.world.atmosphere.apply_preset("sunset")
    eng._apply_sky(rebuild=True)
    _step(eng, 8)
    eng.screenshot_to(out / "07_flight_sunset.png")
    eng.debug_perf = True
    _step(eng, 4)
    eng.screenshot_to(out / "08_performance_overlay.png")
    print(f"wrote {out}")
    p50, p95, p99, pmax = eng.profiler.percentiles()
    print(f"frame p50={p50:.1f} p95={p95:.1f} p99={p99:.1f} max={pmax:.1f}")
    eng.close_engine()


if __name__ == "__main__":
    main()
