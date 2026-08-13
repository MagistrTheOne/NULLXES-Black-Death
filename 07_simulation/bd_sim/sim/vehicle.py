"""Vehicle wrapper — physics owner. No PWM. No ArduPlane."""

from __future__ import annotations

from .dynamics import AeroParams, EnergyAero, VehicleState


class Vehicle:
    def __init__(self, params: AeroParams | None = None) -> None:
        self.aero = EnergyAero(params)
        self.state = VehicleState()

    def reset(self) -> None:
        self.state = VehicleState()

    def step(
        self,
        dt: float,
        *,
        pitch_cmd: float,
        roll_cmd: float,
        yaw_cmd: float,
        throttle_cmd: float,
        launch: bool,
    ) -> list[str]:
        return self.aero.step(
            self.state,
            dt,
            pitch_cmd=pitch_cmd,
            roll_cmd=roll_cmd,
            yaw_cmd=yaw_cmd,
            throttle_cmd=throttle_cmd,
            launch=launch,
        )
