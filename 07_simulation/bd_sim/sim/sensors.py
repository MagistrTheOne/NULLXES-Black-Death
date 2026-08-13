"""S1 derived sensors — functions of VehicleState, not IMU/GPS hardware models."""

from __future__ import annotations

from .dynamics import VehicleState


def derived(state: VehicleState) -> dict:
    return {
        "gps_x": state.x,
        "gps_y": state.y,
        "alt_m": state.z,
        "airspeed_mps": state.airspeed,
        "yaw_deg": state.yaw_deg,
        "pitch_deg": state.pitch_deg,
        "roll_deg": state.roll_deg,
        "ax_approx": 0.0,
        "baro_m": state.z,
    }
