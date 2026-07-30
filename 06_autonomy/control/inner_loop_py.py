"""Python L0 inner-loop — gains match 05_avionics/flight_software/inner_loop.cpp."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class SetpointPy:
    roll_rad: float = 0.0
    pitch_rad: float = 0.0
    yaw_rate_rps: float = 0.0
    thrust_norm: float = 0.0
    valid: bool = False


@dataclass
class ImuPy:
    """accel_mps2: linear acceleration, gravity removed by driver."""

    gyro_rps: tuple[float, float, float] = (0.0, 0.0, 0.0)
    accel_mps2: tuple[float, float, float] = (0.0, 0.0, 0.0)


@dataclass
class ActuatorPy:
    elevon_left: float = 0.0
    elevon_right: float = 0.0
    motor_main: tuple[float, float] = (0.0, 0.0)


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


class InnerLoopPy:
    DT = 0.002

    def __init__(self) -> None:
        self.last_good = SetpointPy()
        self.hold_mode = False
        self.integ_roll = 0.0
        self.integ_pitch = 0.0
        self.kp_att = 2.5
        self.kp_rate = 0.15
        self.kd_rate = 0.01
        self.kp_yaw = 0.2
        self.idle_thrust = 0.05

    def set_hold_attitude(self) -> None:
        self.hold_mode = True
        self.last_good.valid = False

    def step(self, sp: SetpointPy, imu: ImuPy, dt_s: float) -> ActuatorPy:
        use = sp if sp.valid else self.last_good
        if sp.valid:
            self.last_good = sp
            self.hold_mode = False

        p, q, r = imu.gyro_rps
        roll_err = use.roll_rad - self.integ_roll
        pitch_err = use.pitch_rad - self.integ_pitch
        self.integ_roll += p * dt_s
        self.integ_pitch += q * dt_s

        roll_rate_cmd = _clamp(self.kp_att * roll_err, -2.0, 2.0)
        pitch_rate_cmd = _clamp(self.kp_att * pitch_err, -2.0, 2.0)
        yaw_rate_cmd = use.yaw_rate_rps

        roll_u = self.kp_rate * (roll_rate_cmd - p) + self.kd_rate * (-p)
        pitch_u = self.kp_rate * (pitch_rate_cmd - q) + self.kd_rate * (-q)
        yaw_u = self.kp_yaw * (yaw_rate_cmd - r)

        elev_l = _clamp(pitch_u + roll_u, -1.0, 1.0)
        elev_r = _clamp(pitch_u - roll_u, -1.0, 1.0)
        yaw_mix = _clamp(yaw_u, -0.25, 0.25)
        t = _clamp(use.thrust_norm, 0.0, 1.0)
        m0 = _clamp(t - yaw_mix, 0.0, 1.0)
        m1 = _clamp(t + yaw_mix, 0.0, 1.0)

        if self.hold_mode:
            elev_l = _clamp(-self.kp_rate * p, -0.3, 0.3)
            elev_r = _clamp(-self.kp_rate * q, -0.3, 0.3)
            m0 = m1 = self.idle_thrust

        return ActuatorPy(elev_l, elev_r, (m0, m1))
