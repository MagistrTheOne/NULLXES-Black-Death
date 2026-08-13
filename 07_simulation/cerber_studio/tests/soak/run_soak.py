"""60-minute JUST FLY soak. Offscreen BLACKBOX runtime, not a product UI demo."""

from __future__ import annotations

import argparse
import json
import math
import random
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import yaml

from studio.aircraft.registry import AircraftRegistry
from studio.blackbox.recorder import load_replay
from studio.config.paths import user_dir
from studio.config.settings import UserSettings
from studio.sim.vehicle import ControlInput
from studio.sim.world_contract import aircraft_profile_hash, build_contract
from studio.viewport import StudioEngine
from studio.world_gen.weather import sun_from_clock
from studio.world_gen.world_profile import list_profiles


def _clock_label(h: float) -> str:
    return f"{int(h) % 24:02d}:{int((h % 1.0) * 60):02d}"


class SoakPilot:
    def __init__(self, engine: StudioEngine) -> None:
        self.engine = engine
        self.launched = False
        self.turn_t = 0.0
        self.heading_cmd = engine.dynamics.state.yaw_deg

    def command(self, frac: float) -> ControlInput:
        v = self.engine.vehicle
        af = self.engine.world.graph.airfields[0] if self.engine.world.graph.airfields else None
        if not self.launched:
            self.engine.dynamics.control.throttle = 0.85
            self.engine.dynamics.state.throttle = 0.85
            if self.engine.dynamics.can_launch() or v.flight_phase in ("GROUND", "READY"):
                self.engine.launch()
                self.launched = True
            return ControlInput(0.05, 0.0, 0.0, 1.0, "MANUAL")
        if frac >= 0.90 and af is not None:
            dx, dy = af.x - v.x, af.y - v.y
            desired = math.degrees(math.atan2(dx, dy))
            err = (desired - v.heading + 180.0) % 360.0 - 180.0
            yaw = max(-1.0, min(1.0, err / 35.0))
            pitch = 0.15 if v.altitude_agl > 40.0 else -0.12
            thr = 0.25 if v.altitude_agl < 25.0 else 0.45
            return ControlInput(pitch, max(-0.35, min(0.35, yaw * 0.4)), yaw * 0.2, thr, "MANUAL")
        self.turn_t += 1.0
        if self.turn_t > 18.0:
            self.heading_cmd = (self.heading_cmd + 38.0) % 360.0
            self.turn_t = 0.0
        err = (self.heading_cmd - v.heading + 180.0) % 360.0 - 180.0
        yaw = max(-1.0, min(1.0, err / 40.0))
        pitch = 0.12 if v.altitude_agl < 70.0 else (-0.08 if v.altitude_agl > 130.0 else 0.02)
        return ControlInput(pitch, max(-0.4, min(0.4, yaw * 0.45)), yaw * 0.15, 0.78, "MANUAL")


def _accept(summary: dict, discovered: list[str], replay_ok: bool, poi_lost: bool) -> dict:
    ram_growth = float(summary.get("ram_mb_growth") or 0.0)
    checks = {
        "no_crash": not summary.get("crashed"),
        "no_audio_dropout": int(summary.get("audio_underruns") or 0) == 0,
        "no_simulation_spiral": not summary.get("simulation_spiral"),
        "no_duplicate_activity": int(summary.get("duplicate_activity") or 0) == 0,
        "no_disappearing_poi": not poi_lost,
        "no_recorder_corruption": int(summary.get("recorder_queue_lag") or 0) < 40,
        "replay_reaches_final_state": replay_ok,
        "ram_does_not_continuously_grow": ram_growth < 420.0,
        "physics_not_starved": int(summary.get("physics_tick_misses") or 0) < max(30, int(summary.get("physics_ticks") or 1) * 0.02),
    }
    return {"passed": all(checks.values()), "checks": checks, "discovered": discovered}


def run_soak(*, minutes: float, seed: int, region: str, cerber: bool, music: bool, aircraft_id: str) -> dict:
    profiles = list_profiles()
    if region in ("random", ""):
        region = random.choice([p.id for p in profiles])
    cfg = UserSettings()
    cfg.session.world_seed = seed
    cfg.session.region_id = region
    cfg.session.weather = "clear"
    cfg.session.time_flow = "4x"
    cfg.simulation.launch_assist = True
    cfg.simulation.wind = "low"
    engine = StudioEngine(width=960, height=540, settings=cfg)
    registry = AircraftRegistry()
    registry.scan()
    defn = registry.get_or_first(aircraft_id)
    engine.apply_definition(defn)
    engine.set_scene_mode("flight")
    t_gen0 = time.perf_counter()
    engine.prepare_world()
    engine.world.atmosphere.apply_preset("clear")
    engine.world.atmosphere.time_of_day_h = 16.5
    engine.world.atmosphere.time_flow = "4x"
    engine.world.atmosphere.sun_elevation, engine.world.atmosphere.sun_azimuth = sun_from_clock(16.5)
    engine._apply_sky(rebuild=True)
    engine.spawn_ready()
    engine.reset_target()
    engine.paused = False
    engine.input_enabled = True
    contract = build_contract(
        seed=seed,
        region=region,
        aircraft_id=defn.id,
        profile_hash=aircraft_profile_hash(defn),
        dynamics_backend=getattr(engine.dynamics, "name", "arcade"),
        initial_time="16:30",
        time_flow="4x",
    )
    engine.blackbox_contract = contract
    flight_dir = engine.blackbox.start({"soak": True, **contract})
    engine.runtime.world_gen_ms = float(engine.world.gen_ms or (time.perf_counter() - t_gen0) * 1000.0)

    audio = None
    if music:
        try:
            from studio.audio.audio_manager import AudioManager

            audio = AudioManager()
            audio.apply(cfg.audio)
            audio.set_scene("flight")
        except Exception:
            audio = None

    worker = None
    pub = None
    if cerber:
        try:
            from studio.session import WORKER_SCRIPT
            from studio.ipc import DEFAULT_FRAME_ENDPOINT, FramePublisher
            import subprocess

            pub = FramePublisher(DEFAULT_FRAME_ENDPOINT)
            worker = subprocess.Popen(
                [sys.executable, str(WORKER_SCRIPT), "--config", "detector_alpha_v2.yaml"],
                cwd=str(ROOT),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception:
            worker = None

    pilot = SoakPilot(engine)
    discovered: list[str] = []
    poi_lost = False
    wall0 = time.perf_counter()
    budget = max(2.0, minutes * 60.0)
    last_rec = 0.0
    while time.perf_counter() - wall0 < budget:
        frac = (time.perf_counter() - wall0) / budget
        engine.soak_cmd = pilot.command(frac)
        t0 = time.perf_counter()
        engine.step_world()
        dt = time.perf_counter() - t0
        now = time.perf_counter()
        if now - last_rec >= 0.05:
            sample = engine.record_sample()
            if engine.blackbox.tick(0.05, sample):
                engine.runtime.recorder_writes += 1
            engine.runtime.recorder_expected = int(engine.vehicle.timestamp * 20)
            last_rec = now
        for title in engine.discovered_now:
            if title not in discovered:
                discovered.append(title)
        titles = {str(lm.extra.get("title") or lm.kind.upper()) for lm in engine.world.graph.landmarks}
        if any(name not in titles for name in discovered):
            poi_lost = True
        if audio is not None:
            try:
                audio.throttle = engine.vehicle.throttle
                audio.airspeed = engine.vehicle.airspeed
            except Exception:
                engine.runtime.audio_underruns += 1
        if worker is not None and pub is not None and engine.runtime.frames % 3 == 0:
            t_c = time.perf_counter()
            try:
                pub.send(engine.sample_cerber_bgr(), {"source": "nose"})
                engine.runtime.cerber_latency_ms.append((time.perf_counter() - t_c) * 1000.0)
            except Exception:
                pass
        v = engine.vehicle
        if v.flight_phase in ("STOPPED", "CRASHED") and frac > 0.92:
            break
        if dt < 0.008:
            time.sleep(0.008 - dt)

    engine.blackbox.event("SOAK_END", {"phase": engine.vehicle.flight_phase}, t=engine.vehicle.timestamp)
    engine.blackbox.close()
    poses_ok = False
    meta, poses, events = load_replay(flight_dir)
    engine.start_replay(flight_dir)
    if poses:
        engine.replay_i = 0
        guard = 0
        while engine.replay_active and guard < len(poses) + 8:
            engine.step_world()
            guard += 1
        last = poses[-1]
        now = engine.vehicle
        poses_ok = abs(now.x - float(last["x"])) < 25.0 and abs(now.y - float(last["y"])) < 25.0
        poses_ok = poses_ok and bool(poses) and not engine.replay_active
    wall_s = time.perf_counter() - wall0
    summary = engine.runtime.summary(wall_s=wall_s, sim_s=float(engine.vehicle.timestamp))
    summary["region"] = region
    summary["seed"] = seed
    summary["tod_end"] = _clock_label(engine.world.atmosphere.clock_h)
    summary["flight_dir"] = str(flight_dir)
    summary["replay_warning"] = engine.replay_warning
    summary["contract"] = contract
    verdict = _accept(summary, discovered, poses_ok, poi_lost)
    if worker is not None:
        worker.terminate()
    engine.close_engine()
    report = {"summary": summary, "acceptance": verdict, "events": len(events), "poses": len(poses)}
    out_dir = user_dir() / "soak"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "last.yaml"
    path.write_text(yaml.safe_dump(report, allow_unicode=True, sort_keys=False), encoding="utf-8")
    (out_dir / "last.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def main() -> int:
    p = argparse.ArgumentParser(description="BLACKBOX JUST FLY soak-test")
    p.add_argument("--minutes", type=float, default=60.0)
    p.add_argument("--seed", type=int, default=1947)
    p.add_argument("--region", default="random")
    p.add_argument("--aircraft", default="skywalker_x8")
    p.add_argument("--cerber", action="store_true", default=True)
    p.add_argument("--no-cerber", action="store_true")
    p.add_argument("--music", action="store_true", default=True)
    p.add_argument("--no-music", action="store_true")
    args = p.parse_args()
    report = run_soak(
        minutes=args.minutes,
        seed=args.seed,
        region=args.region,
        cerber=bool(args.cerber) and not args.no_cerber,
        music=bool(args.music) and not args.no_music,
        aircraft_id=args.aircraft,
    )
    print(yaml.safe_dump(report["acceptance"], allow_unicode=True))
    print(f"report: {user_dir() / 'soak' / 'last.yaml'}")
    return 0 if report["acceptance"]["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
