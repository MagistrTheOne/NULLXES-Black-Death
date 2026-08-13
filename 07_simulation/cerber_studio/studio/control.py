"""Keyboard targets → smoothed control surfaces. Frame-rate independent."""

from __future__ import annotations

import math
from dataclasses import dataclass


def _exp_approach(current: float, target: float, rate: float, dt: float) -> float:
    k = 1.0 - math.exp(-max(0.0, rate) * dt)
    return current + (target - current) * k


@dataclass
class ControlState:
    pitch: float = 0.0
    roll: float = 0.0
    yaw: float = 0.0
    throttle: float = 0.0
    target_pitch: float = 0.0
    target_roll: float = 0.0
    target_yaw: float = 0.0
    throttle_dir: float = 0.0

    pitch_response: float = 9.0
    roll_response: float = 10.0
    yaw_response: float = 8.0
    pitch_return: float = 5.5
    roll_return: float = 6.0
    yaw_return: float = 6.5
    throttle_per_sec: float = 0.55

    def set_targets(self, pitch: float, roll: float, yaw: float, throttle_dir: float) -> None:
        self.target_pitch = max(-1.0, min(1.0, pitch))
        self.target_roll = max(-1.0, min(1.0, roll))
        self.target_yaw = max(-1.0, min(1.0, yaw))
        self.throttle_dir = max(-1.0, min(1.0, throttle_dir))

    def _axis(self, current: float, target: float, rise: float, fall: float, dt: float) -> float:
        rate = rise if abs(target) >= 0.05 else fall
        return _exp_approach(current, target, rate, dt)

    def step(self, dt: float, *, sensitivity: float = 1.0) -> None:
        sens = max(0.2, min(2.0, sensitivity))
        self.pitch = self._axis(
            self.pitch, self.target_pitch, self.pitch_response * sens, self.pitch_return, dt
        )
        self.roll = self._axis(
            self.roll, self.target_roll, self.roll_response * sens, self.roll_return, dt
        )
        self.yaw = self._axis(
            self.yaw, self.target_yaw, self.yaw_response * sens, self.yaw_return, dt
        )
        self.throttle = max(
            0.0,
            min(1.0, self.throttle + self.throttle_dir * self.throttle_per_sec * dt),
        )

    def reset(self, throttle: float = 0.0) -> None:
        self.pitch = self.roll = self.yaw = 0.0
        self.target_pitch = self.target_roll = self.target_yaw = 0.0
        self.throttle_dir = 0.0
        self.throttle = float(max(0.0, min(1.0, throttle)))
