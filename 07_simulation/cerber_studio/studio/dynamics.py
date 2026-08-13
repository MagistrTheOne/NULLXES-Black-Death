"""Arcade fixed-wing dynamics — launch, flight, approach, touchdown, ground roll."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

import numpy as np

from .control import ControlState

PHYSICS_DT = 0.01
LAUNCH_MIN_THROTTLE = 0.70
SIT_HEIGHT = 0.55
AIRBORNE_PHASES = frozenset(
    {"LAUNCH", "AIRBORNE", "FLIGHT", "APPROACH", "TOUCHDOWN"}
)


class FlightPhase(str, Enum):
    GROUND = "GROUND"
    READY = "READY"
    LAUNCH = "LAUNCH"
    AIRBORNE = "AIRBORNE"
    FLIGHT = "FLIGHT"
    APPROACH = "APPROACH"
    TOUCHDOWN = "TOUCHDOWN"
    GROUND_ROLL = "GROUND_ROLL"
    STOPPED = "STOPPED"
    LANDED = "STOPPED"
    CRASHED = "CRASHED"


class LandingGrade(str, Enum):
    NONE = ""
    CLEAN = "CLEAN"
    HARD = "HARD"
    CRASH = "CRASH"


@dataclass
class WingParams:
    key: str
    title: str
    scale: float
    max_speed: float
    turn_rate_deg: float
    color_rgb: tuple[float, float, float]
    accent_rgb: tuple[float, float, float]
    stall_speed: float = 10.0
    cruise_speed: float = 18.0
    max_pitch_rate: float = 55.0
    max_roll_rate: float = 90.0
    max_yaw_rate: float = 28.0


def preset(key: str) -> WingParams:
    return PRESETS.get(key, PRESETS["ar_wing"])


PRESETS: dict[str, WingParams] = {
    "s800": WingParams(
        key="s800",
        title="Reptile S800-class",
        scale=1.0,
        max_speed=28.0,
        turn_rate_deg=95.0,
        color_rgb=(0.14, 0.15, 0.16),
        accent_rgb=(0.86, 0.35, 0.16),
        stall_speed=9.0,
        cruise_speed=16.0,
    ),
    "ar_wing": WingParams(
        key="ar_wing",
        title="AR Wing Pro-class",
        scale=1.35,
        max_speed=34.0,
        turn_rate_deg=75.0,
        color_rgb=(0.05, 0.05, 0.055),
        accent_rgb=(0.70, 0.12, 0.16),
        stall_speed=10.0,
        cruise_speed=18.0,
    ),
}


@dataclass
class PoseState:
    x: float = 0.0
    y: float = 0.0
    z: float = SIT_HEIGHT
    pitch_deg: float = 0.0
    yaw_deg: float = 0.0
    roll_deg: float = 0.0
    speed: float = 0.0
    throttle: float = 0.0
    pitch_rate: float = 0.0
    roll_rate: float = 0.0
    yaw_rate: float = 0.0
    ground_z: float = 0.0
    airborne: bool = False
    phase: FlightPhase = FlightPhase.GROUND
    launch_age: float = 0.0
    agl: float = SIT_HEIGHT
    vz: float = 0.0
    trim_pitch: float = 0.0
    trim_roll: float = 0.0
    landing_grade: str = ""
    on_runway: bool = False
    flight_time: float = 0.0
    distance_m: float = 0.0
    max_alt: float = 0.0
    max_speed: float = 0.0
    stalling: bool = False
    overspeed: bool = False


class ArcadeDynamics:
    def __init__(self, params: WingParams) -> None:
        self.params = params
        self.state = PoseState()
        self.control = ControlState()
        self._launch_assist = True
        self._auto_level = False
        self._runway_yaw = 0.0

    def reset(self, *, x: float = 0.0, y: float = 0.0, yaw_deg: float = 0.0, ground_z: float = 0.0) -> None:
        self.state = PoseState(
            x=x,
            y=y,
            z=ground_z + SIT_HEIGHT,
            yaw_deg=yaw_deg,
            ground_z=ground_z,
            agl=SIT_HEIGHT,
            phase=FlightPhase.GROUND,
            on_runway=True,
        )
        self.control.reset(0.0)

    def set_params(self, params: WingParams) -> None:
        self.params = params

    def set_launch_assist(self, on: bool) -> None:
        self._launch_assist = bool(on)

    def set_auto_level(self, on: bool) -> None:
        self._auto_level = bool(on)

    def can_launch(self) -> bool:
        return self.state.phase in (
            FlightPhase.GROUND,
            FlightPhase.READY,
            FlightPhase.STOPPED,
            FlightPhase.LANDED,
        ) and (self.control.throttle >= LAUNCH_MIN_THROTTLE)

    def request_launch(self) -> bool:
        if not self.can_launch():
            return False
        p = self.params
        s = self.state
        s.phase = FlightPhase.LAUNCH
        s.airborne = True
        s.launch_age = 0.0
        s.landing_grade = ""
        s.throttle = max(s.throttle, LAUNCH_MIN_THROTTLE)
        self.control.throttle = s.throttle
        s.speed = max(p.stall_speed * 1.12, p.max_speed * 0.42)
        s.pitch_deg = 8.0
        s.roll_deg = 0.0
        s.pitch_rate = 6.0
        s.roll_rate = 0.0
        s.yaw_rate = 0.0
        s.z = s.ground_z + SIT_HEIGHT + 1.4
        return True

    def _authority(self) -> float:
        p = self.params
        s = self.state
        if s.phase in (FlightPhase.GROUND, FlightPhase.STOPPED, FlightPhase.LANDED, FlightPhase.CRASHED):
            return 0.0
        frac = (s.speed - p.stall_speed * 0.45) / max(4.0, p.cruise_speed - p.stall_speed * 0.45)
        return float(np.clip(frac, 0.12, 1.0))

    def _assist_blend(self) -> float:
        if not self._launch_assist:
            return 0.0
        s = self.state
        if s.phase == FlightPhase.LAUNCH:
            return 1.0
        if s.phase == FlightPhase.AIRBORNE:
            return float(np.clip(1.0 - s.launch_age / 1.8, 0.0, 1.0))
        return 0.0

    def step(
        self,
        dt: float,
        *,
        pitch_cmd: float,
        roll_cmd: float,
        yaw_cmd: float,
        throttle_cmd: float,
        assist_yaw: float = 0.0,
        wind_xy: tuple[float, float] = (0.0, 0.0),
        sim_speed: float = 1.0,
        ground_collision: bool = True,
        difficulty: str = "standard",
        fail_throttle: bool = False,
        ground_z: float | None = None,
        on_runway: bool = False,
        runway_yaw: float = 0.0,
        gust_xy: tuple[float, float] = (0.0, 0.0),
        flight_mode: str = "MANUAL",
        trim_cmd: float = 0.0,
    ) -> PoseState:
        dt = float(max(1e-4, min(0.05, dt))) * float(max(0.25, min(2.0, sim_speed)))
        p = self.params
        s = self.state
        if ground_z is not None:
            s.ground_z = float(ground_z)
        s.on_runway = bool(on_runway)
        self._runway_yaw = float(runway_yaw)

        self.control.set_targets(pitch_cmd, roll_cmd, yaw_cmd, throttle_cmd)
        self.control.step(dt, sensitivity=float(getattr(self, "_sensitivity", 1.0)))
        s.throttle = self.control.throttle
        if fail_throttle:
            s.throttle = float(max(0.0, s.throttle * (1.0 - 0.35 * dt)))
            self.control.throttle = s.throttle

        if trim_cmd:
            s.trim_pitch = float(np.clip(s.trim_pitch + trim_cmd * 8.0 * dt, -12.0, 12.0))

        if s.phase in (FlightPhase.GROUND, FlightPhase.READY, FlightPhase.STOPPED, FlightPhase.LANDED, FlightPhase.CRASHED):
            return self._step_ground(dt)
        if s.phase == FlightPhase.GROUND_ROLL:
            return self._step_ground_roll(dt, wind_xy, gust_xy)

        return self._step_air(
            dt,
            assist_yaw=assist_yaw,
            wind_xy=wind_xy,
            gust_xy=gust_xy,
            ground_collision=ground_collision,
            difficulty=difficulty,
            flight_mode=flight_mode,
        )

    def _step_air(
        self,
        dt: float,
        *,
        assist_yaw: float,
        wind_xy: tuple[float, float],
        gust_xy: tuple[float, float],
        ground_collision: bool,
        difficulty: str,
        flight_mode: str,
    ) -> PoseState:
        p = self.params
        s = self.state
        z0 = s.z
        x0, y0 = s.x, s.y
        diff = (difficulty or "standard").lower()
        rate_mul = {"arcade": 1.15, "strict": 0.78}.get(diff, 1.0)
        sink_mul = {"arcade": 0.75, "strict": 1.25}.get(diff, 1.0)
        auth = self._authority() * rate_mul
        assist = self._assist_blend()
        mode = (flight_mode or "MANUAL").upper()
        auto = 1.0 if (self._auto_level or mode == "ASSIST") else 0.0

        pitch_in = self.control.pitch
        roll_in = self.control.roll * (1.0 - 0.72 * assist)
        yaw_in = self.control.yaw + assist_yaw + roll_in * 0.22 * auto

        des_pr = (pitch_in * p.max_pitch_rate + s.trim_pitch * 2.4) * auth
        des_rr = (roll_in * p.max_roll_rate + s.trim_roll * 2.0) * auth
        des_yr = yaw_in * p.max_yaw_rate * auth * 0.45
        s.pitch_rate += (des_pr - s.pitch_rate) * min(1.0, 6.5 * dt)
        s.roll_rate += (des_rr - s.roll_rate) * min(1.0, 7.0 * dt)
        s.yaw_rate += (des_yr - s.yaw_rate) * min(1.0, 5.0 * dt)
        s.pitch_rate *= max(0.0, 1.0 - 1.8 * dt)
        s.roll_rate *= max(0.0, 1.0 - 1.4 * dt)
        s.yaw_rate *= max(0.0, 1.0 - 2.2 * dt)

        if assist > 0.0:
            s.roll_deg *= max(0.0, 1.0 - 2.4 * assist * dt)
            s.pitch_deg += (8.0 - s.pitch_deg) * 0.55 * assist * dt
            s.roll_rate *= 1.0 - 0.65 * assist

        if auto > 0.0 and abs(roll_in) < 0.08 and abs(pitch_in) < 0.08:
            s.roll_deg *= max(0.0, 1.0 - 1.8 * auto * dt)
            s.pitch_deg += (2.5 - s.pitch_deg) * 0.55 * auto * dt

        s.pitch_deg = float(np.clip(s.pitch_deg + s.pitch_rate * dt, -48.0, 42.0))
        s.roll_deg = float(np.clip(s.roll_deg + s.roll_rate * dt, -62.0, 62.0))
        if abs(roll_in) < 0.04 and assist <= 0.0 and auto <= 0.0:
            s.roll_deg *= max(0.0, 1.0 - 0.55 * dt)

        bank = np.radians(s.roll_deg)
        spd = max(6.0, s.speed)
        turn_from_bank = np.degrees(np.tan(bank) * 9.81 / spd)
        s.yaw_deg = (s.yaw_deg + (turn_from_bank + s.yaw_rate) * dt) % 360.0

        pr = np.radians(s.pitch_deg)
        yr = np.radians(s.yaw_deg)
        forward = np.array(
            [np.sin(yr) * np.cos(pr), np.cos(yr) * np.cos(pr), np.sin(pr)],
            dtype=np.float64,
        )

        thrust = s.throttle * p.max_speed
        drag = 0.42 * s.speed
        energy = -9.81 * np.sin(pr) * 0.55
        s.speed += (thrust - drag + energy) * dt * 0.55
        stall = p.stall_speed
        s.stalling = s.speed < stall
        if s.stalling:
            s.speed = max(2.0, s.speed - (stall - s.speed) * 0.35 * dt)
            if auto > 0.0:
                s.pitch_deg = min(s.pitch_deg, max(-8.0, s.pitch_deg - 18.0 * dt))
            else:
                s.pitch_deg = min(s.pitch_deg, s.pitch_deg * 0.92)
        s.overspeed = s.speed > p.max_speed * 1.08
        if s.overspeed:
            s.pitch_deg += float(np.sin(s.flight_time * 22.0) * 4.0 * dt)
            s.speed = min(s.speed, p.max_speed * 1.18)
        s.speed = float(np.clip(s.speed, 0.0, p.max_speed * 1.18))

        lift = min(1.15, (s.speed / max(8.0, p.cruise_speed)) * (0.75 + 0.35 * s.throttle))
        sink = -9.81 * (1.0 - lift) * 0.22 * sink_mul
        if s.stalling:
            sink -= (stall - s.speed) * 0.45

        vel = forward * s.speed
        s.x += float(vel[0] * dt + wind_xy[0] * dt + gust_xy[0] * dt)
        s.y += float(vel[1] * dt + wind_xy[1] * dt + gust_xy[1] * dt)
        s.z += float(vel[2] * dt + sink * dt)
        s.vz = (s.z - z0) / max(1e-4, dt)
        s.distance_m += float(np.hypot(s.x - x0, s.y - y0))
        s.flight_time += dt
        s.max_alt = max(s.max_alt, s.agl)
        s.max_speed = max(s.max_speed, s.speed)

        s.launch_age += dt
        floor = s.ground_z + SIT_HEIGHT
        s.agl = s.z - s.ground_z

        if s.phase == FlightPhase.LAUNCH:
            if s.launch_age >= 0.45:
                s.phase = FlightPhase.AIRBORNE
        elif s.phase == FlightPhase.AIRBORNE:
            if s.launch_age >= 1.6 and s.speed > stall * 0.95 and s.agl > 3.0:
                s.phase = FlightPhase.FLIGHT
            elif s.launch_age >= 2.2:
                s.phase = FlightPhase.FLIGHT
        elif s.phase == FlightPhase.FLIGHT:
            if s.agl < 28.0 and s.vz < -0.4 and s.pitch_deg < 6.0:
                s.phase = FlightPhase.APPROACH
        elif s.phase == FlightPhase.APPROACH:
            if s.agl > 40.0:
                s.phase = FlightPhase.FLIGHT

        if ground_collision and s.z <= floor:
            self._touchdown(floor)
        return s

    def _align_err(self) -> float:
        s = self.state
        return abs((s.yaw_deg - self._runway_yaw + 180.0) % 360.0 - 180.0)

    def _touchdown(self, floor: float) -> None:
        s = self.state
        impact_vz = abs(min(0.0, s.vz))
        align = self._align_err()
        pitch = s.pitch_deg
        s.z = floor
        s.agl = SIT_HEIGHT
        s.airborne = False
        if impact_vz > 9.5 or pitch < -22.0 or (not s.on_runway and impact_vz > 5.0):
            s.phase = FlightPhase.CRASHED
            s.landing_grade = LandingGrade.CRASH.value
            s.speed = 0.0
            s.pitch_deg = 0.0
            s.roll_deg = 0.0
            s.pitch_rate = s.roll_rate = s.yaw_rate = 0.0
            return
        hard = impact_vz > 4.2 or align > 28.0 or not s.on_runway
        s.landing_grade = LandingGrade.HARD.value if hard else LandingGrade.CLEAN.value
        s.phase = FlightPhase.TOUCHDOWN
        s.pitch_deg = 0.0
        s.roll_deg *= 0.2
        s.pitch_rate = s.roll_rate = 0.0
        s.speed *= 0.82
        s.phase = FlightPhase.GROUND_ROLL

    def _step_ground_roll(self, dt: float, wind_xy: tuple[float, float], gust_xy: tuple[float, float]) -> PoseState:
        s = self.state
        s.airborne = False
        s.z = s.ground_z + SIT_HEIGHT
        s.agl = SIT_HEIGHT
        s.pitch_deg *= max(0.0, 1.0 - 6.0 * dt)
        s.roll_deg *= max(0.0, 1.0 - 6.0 * dt)
        yaw_in = self.control.yaw
        s.yaw_deg = (s.yaw_deg + yaw_in * 42.0 * dt * min(1.0, s.speed / 8.0)) % 360.0
        idle = max(0.0, s.throttle - 0.12)
        s.speed += idle * 6.0 * dt
        s.speed *= max(0.0, 1.0 - 0.55 * dt)
        s.speed = max(0.0, s.speed - 4.8 * dt)
        yr = np.radians(s.yaw_deg)
        s.x += (np.sin(yr) * s.speed + wind_xy[0] * 0.15 + gust_xy[0] * 0.1) * dt
        s.y += (np.cos(yr) * s.speed + wind_xy[1] * 0.15 + gust_xy[1] * 0.1) * dt
        s.vz = 0.0
        s.flight_time += dt
        s.distance_m += s.speed * dt
        if s.speed < 0.45 and s.throttle < 0.12:
            s.speed = 0.0
            s.phase = FlightPhase.STOPPED
            s.pitch_rate = s.roll_rate = s.yaw_rate = 0.0
        return s

    def _step_ground(self, dt: float) -> PoseState:
        s = self.state
        s.speed = 0.0
        s.airborne = False
        s.pitch_deg *= max(0.0, 1.0 - 8.0 * dt)
        s.roll_deg *= max(0.0, 1.0 - 8.0 * dt)
        s.pitch_rate = s.roll_rate = s.yaw_rate = 0.0
        s.z = s.ground_z + SIT_HEIGHT
        s.agl = SIT_HEIGHT
        s.vz = 0.0
        if s.phase == FlightPhase.CRASHED:
            return s
        if s.throttle >= LAUNCH_MIN_THROTTLE:
            s.phase = FlightPhase.READY
        elif s.phase not in (FlightPhase.STOPPED, FlightPhase.LANDED):
            s.phase = FlightPhase.GROUND
        return s

    def position(self) -> tuple[float, float, float]:
        s = self.state
        return s.x, s.y, s.z

    def hpr(self) -> tuple[float, float, float]:
        s = self.state
        return s.yaw_deg, s.pitch_deg, s.roll_deg

    def launch_cue(self) -> str:
        s = self.state
        if s.phase in (
            FlightPhase.LAUNCH,
            FlightPhase.AIRBORNE,
            FlightPhase.FLIGHT,
            FlightPhase.APPROACH,
            FlightPhase.TOUCHDOWN,
            FlightPhase.GROUND_ROLL,
        ):
            return ""
        if s.phase == FlightPhase.CRASHED:
            return "CRASHED"
        if s.phase == FlightPhase.STOPPED:
            return "FLIGHT COMPLETE"
        if s.throttle < LAUNCH_MIN_THROTTLE:
            return "THROTTLE UP TO LAUNCH"
        return "READY FOR LAUNCH"
