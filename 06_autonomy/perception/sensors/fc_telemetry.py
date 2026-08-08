"""FC telemetry decode → SoftBus IMU / GNSS / Nav (ENU)."""

from __future__ import annotations

import math
import time
from dataclasses import dataclass

from soft_bus.messages import GnssFix, ImuMsg, NavStateMsg


@dataclass(frozen=True)
class FcTelemetry:
    """Decoded FC sample (MAVLink or native). Body/NED inputs converted at map."""

    # Attitude
    roll_rad: float = 0.0
    pitch_rad: float = 0.0
    yaw_rad: float = 0.0  # NED heading from north; converted to ENU yaw
    # Local position NED [m]
    north_m: float = 0.0
    east_m: float = 0.0
    down_m: float = 0.0
    vn_mps: float = 0.0
    ve_mps: float = 0.0
    vd_mps: float = 0.0
    # IMU body (FC frame) — gyro [rad/s], accel including gravity [m/s^2]
    gyro_x: float = 0.0
    gyro_y: float = 0.0
    gyro_z: float = 0.0
    accel_x: float = 0.0
    accel_y: float = 0.0
    accel_z: float = 0.0
    # GNSS
    lat_deg: float = 0.0
    lon_deg: float = 0.0
    alt_amsl_m: float = 0.0
    fix_ok: bool = False
    hdop: float = 99.0
    # Timing
    time_boot_ms: int = 0
    sensor_stamp_ns: int = 0


def ned_yaw_to_enu(yaw_ned: float) -> float:
    """ArduPilot yaw (from North toward East) → SoftBus ENU yaw (from East toward North)."""
    return (math.pi / 2.0) - yaw_ned


def ned_pos_to_enu(north: float, east: float, down: float) -> tuple[float, float, float]:
    return east, north, -down


def ned_vel_to_enu(vn: float, ve: float, vd: float) -> tuple[float, float, float]:
    return ve, vn, -vd


def map_fc_to_bus(
    fc: FcTelemetry,
    *,
    stamp_ns: int | None = None,
) -> tuple[ImuMsg, GnssFix, NavStateMsg]:
    """Map one FC sample into SoftBus messages (ENU nav)."""
    now_ns = stamp_ns if stamp_ns is not None else time.monotonic_ns()
    sensor_ns = fc.sensor_stamp_ns or (fc.time_boot_ms * 1_000_000)
    stamp_s = now_ns / 1e9

    ex, ey, ez = ned_pos_to_enu(fc.north_m, fc.east_m, fc.down_m)
    vx, vy, vz = ned_vel_to_enu(fc.vn_mps, fc.ve_mps, fc.vd_mps)
    yaw = ned_yaw_to_enu(fc.yaw_rad)

    # Linear accel ENU: rotate body accel minus gravity — coarse; driver may refine.
    # Here publish body rates as-is in body frame; NavEKF expects ENU linear accel.
    # Pass zero linear ENU until attitude rotation is calibrated (SensorHub marks imu_ok).
    imu = ImuMsg(
        gyro_rps=(fc.gyro_x, fc.gyro_y, fc.gyro_z),
        accel_mps2=(0.0, 0.0, 0.0),
        stamp_s=stamp_s,
        stamp_ns=now_ns,
        sensor_stamp_ns=sensor_ns,
        frame_id="body",
    )
    gnss = GnssFix(
        x=ex,
        y=ey,
        z=ez,
        fix_ok=fc.fix_ok,
        stamp_s=stamp_s,
        stamp_ns=now_ns,
        sensor_stamp_ns=sensor_ns,
        frame_id="enu",
        hdop=fc.hdop,
    )
    nav = NavStateMsg(
        x=ex,
        y=ey,
        z=ez,
        vx=vx,
        vy=vy,
        vz=vz,
        yaw=yaw,
        stamp_s=stamp_s,
        stamp_ns=now_ns,
        sensor_stamp_ns=sensor_ns,
        frame_id="enu",
        cov_xx=4.0 if fc.fix_ok else 1.0e6,
        cov_yy=4.0 if fc.fix_ok else 1.0e6,
        cov_zz=9.0 if fc.fix_ok else 1.0e6,
        source="fc",
    )
    return imu, gnss, nav
