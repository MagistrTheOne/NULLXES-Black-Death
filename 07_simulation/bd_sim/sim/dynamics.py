"""S1 energy / point-mass flying-wing. Not JSBSim. Not X8 proof."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

G = 9.81
RHO = 1.225


@dataclass
class AeroParams:
    mass_kg: float = 4.2
    wing_area_m2: float = 0.85
    cl_alpha: float = 4.8
    alpha_stall_deg: float = 14.0
    cd0: float = 0.035
    k_induced: float = 0.07
    thrust_n: float = 38.0
    v_stall: float = 9.5
    v_takeoff: float = 11.0
    v_max: float = 38.0
    roll_rate_dps: float = 70.0
    pitch_rate_dps: float = 45.0
    bank_limit_deg: float = 55.0
    pitch_limit_deg: float = 35.0
    wind_ned: tuple[float, float, float] = (1.5, 0.4, 0.0)


@dataclass
class VehicleState:
    x: float = 0.0
    y: float = 8.0
    z: float = 0.35
    vx: float = 0.0
    vy: float = 0.0
    vz: float = 0.0
    yaw_deg: float = 0.0
    pitch_deg: float = 4.0
    roll_deg: float = 0.0
    throttle: float = 0.0
    launched: bool = False
    crashed: bool = False
    stalled: bool = False
    airspeed: float = 0.0
    alpha_deg: float = 0.0
    t: float = 0.0

    def position(self) -> tuple[float, float, float]:
        return self.x, self.y, self.z

    def hpr(self) -> tuple[float, float, float]:
        return self.yaw_deg, self.pitch_deg, self.roll_deg

    def speed(self) -> float:
        return float(np.hypot(np.hypot(self.vx, self.vy), self.vz))


def _wrap180(deg: float) -> float:
    return float((deg + 180.0) % 360.0 - 180.0)


def _body_forward(yaw_deg: float, pitch_deg: float) -> np.ndarray:
    yr = np.radians(yaw_deg)
    pr = np.radians(pitch_deg)
    return np.array(
        [np.sin(yr) * np.cos(pr), np.cos(yr) * np.cos(pr), np.sin(pr)],
        dtype=np.float64,
    )


class EnergyAero:
    """Lift/drag/thrust/gravity + bank-to-turn. Deterministic, realtime."""

    def __init__(self, params: AeroParams | None = None) -> None:
        self.p = params or AeroParams()

    def step(
        self,
        s: VehicleState,
        dt: float,
        *,
        pitch_cmd: float,
        roll_cmd: float,
        yaw_cmd: float,
        throttle_cmd: float,
        launch: bool,
    ) -> list[str]:
        dt = float(max(1e-4, min(0.05, dt)))
        p = self.p
        flags: list[str] = []
        if s.crashed:
            s.vx = s.vy = s.vz = 0.0
            s.throttle = 0.0
            s.z = 0.0
            return flags

        if launch and not s.launched:
            s.launched = True
            s.throttle = max(s.throttle, 0.85)
            s.vy = max(s.vy, p.v_takeoff * 0.65)
            flags.append("LAUNCH")

        s.throttle = float(np.clip(s.throttle + throttle_cmd * dt * 0.85, 0.0, 1.0))
        if not s.launched:
            s.throttle = min(s.throttle, 0.15)
            s.z = 0.35
            s.vx = s.vy = s.vz = 0.0
            s.airspeed = 0.0
            s.t += dt
            return flags

        s.roll_deg = float(
            np.clip(
                s.roll_deg + roll_cmd * p.roll_rate_dps * dt,
                -p.bank_limit_deg,
                p.bank_limit_deg,
            )
        )
        s.pitch_deg = float(
            np.clip(
                s.pitch_deg + pitch_cmd * p.pitch_rate_dps * dt,
                -p.pitch_limit_deg,
                p.pitch_limit_deg,
            )
        )
        if abs(roll_cmd) < 0.08:
            s.roll_deg *= max(0.0, 1.0 - 1.4 * dt)
        if abs(pitch_cmd) < 0.08:
            s.pitch_deg *= max(0.0, 1.0 - 0.6 * dt)

        v = np.array([s.vx, s.vy, s.vz], dtype=np.float64)
        wind = np.array(p.wind_ned, dtype=np.float64)
        v_air = v - wind
        tas = float(np.linalg.norm(v_air))
        s.airspeed = tas
        gamma = 0.0 if tas < 0.5 else float(np.degrees(np.arcsin(np.clip(v_air[2] / tas, -1.0, 1.0))))
        s.alpha_deg = s.pitch_deg - gamma

        q = 0.5 * RHO * tas * tas
        stalled = abs(s.alpha_deg) > p.alpha_stall_deg or tas < p.v_stall
        s.stalled = stalled
        if stalled:
            flags.append("STALL")
            cl = 0.35 * np.sign(s.alpha_deg) if abs(s.alpha_deg) > 1e-3 else 0.0
            cd = p.cd0 + 0.55
            s.pitch_deg = min(s.pitch_deg, s.pitch_deg - 18.0 * dt)
        else:
            cl = float(np.clip(p.cl_alpha * np.radians(s.alpha_deg), -1.4, 1.4))
            cd = p.cd0 + p.k_induced * cl * cl

        fwd = _body_forward(s.yaw_deg, s.pitch_deg)
        bank = np.radians(s.roll_deg)
        lift_dir = np.array(
            [np.sin(bank) * fwd[1], -np.sin(bank) * fwd[0], np.cos(bank)],
            dtype=np.float64,
        )
        ln = float(np.linalg.norm(lift_dir))
        if ln > 1e-6:
            lift_dir /= ln
        lift = q * p.wing_area_m2 * cl
        drag = q * p.wing_area_m2 * cd
        thrust = p.thrust_n * s.throttle
        drag_dir = -v_air / tas if tas > 0.4 else -fwd
        acc = (
            fwd * (thrust / p.mass_kg)
            + lift_dir * (lift / p.mass_kg)
            + drag_dir * (drag / p.mass_kg)
            + np.array([0.0, 0.0, -G])
        )
        v = v + acc * dt
        s.vx, s.vy, s.vz = float(v[0]), float(v[1]), float(v[2])

        # bank-to-turn (coordinated), plus tiny yaw stick
        v_h = max(tas, p.v_stall * 0.8)
        yaw_rate = np.degrees(G * np.tan(bank) / v_h)
        yaw_rate += yaw_cmd * 25.0
        s.yaw_deg = (s.yaw_deg + yaw_rate * dt) % 360.0

        s.x += s.vx * dt
        s.y += s.vy * dt
        s.z += s.vz * dt

        if not s.launched:
            s.z = max(s.z, 0.35)
        if s.z < 8.0 and s.launched and tas < p.v_takeoff:
            flags.append("LOW_ALTITUDE")
        if abs(s.roll_deg) > p.bank_limit_deg - 0.5:
            flags.append("EXCESSIVE_BANK")
        if tas > p.v_max:
            flags.append("OVERSPEED")
            s.throttle = min(s.throttle, 0.55)

        if s.z <= 0.05:
            impact = tas > 3.5 or abs(s.vz) > 2.0
            s.z = 0.0
            s.vx = s.vy = s.vz = 0.0
            if impact:
                s.crashed = True
                flags.append("CRASH")
            else:
                s.launched = False
                s.throttle = 0.0
                s.z = 0.35

        s.t += dt
        return flags
