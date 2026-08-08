"""Optional pymavlink UART/UDP link → FcTelemetry stream."""

from __future__ import annotations

import time
from dataclasses import dataclass

from .fc_telemetry import FcTelemetry


@dataclass
class MavlinkLinkConfig:
    connection: str = "udp:127.0.0.1:14550"
    # e.g. serial:/dev/ttyUSB0:921600 or udp:0.0.0.0:14550
    timeout_s: float = 1.0


class MavlinkFcLink:
    """Live ArduPilot Plane telemetry. Requires pymavlink at runtime."""

    def __init__(self, cfg: MavlinkLinkConfig | None = None) -> None:
        self.cfg = cfg or MavlinkLinkConfig()
        self._master = None
        self._latest = FcTelemetry()
        self._have_att = False
        self._have_pos = False

    def open(self) -> bool:
        try:
            from pymavlink import mavutil
        except ImportError as e:
            raise RuntimeError("pymavlink required for MavlinkFcLink") from e
        self._master = mavutil.mavlink_connection(self.cfg.connection)
        self._master.wait_heartbeat(timeout=self.cfg.timeout_s)
        return True

    def close(self) -> None:
        self._master = None

    def poll(self) -> FcTelemetry | None:
        if self._master is None:
            return None
        msg = self._master.recv_match(blocking=False)
        if msg is None:
            return None
        t = msg.get_type()
        cur = self._latest
        boot_ms = int(getattr(msg, "time_boot_ms", cur.time_boot_ms) or cur.time_boot_ms)
        sensor_ns = boot_ms * 1_000_000
        if t == "ATTITUDE":
            self._latest = FcTelemetry(
                roll_rad=float(msg.roll),
                pitch_rad=float(msg.pitch),
                yaw_rad=float(msg.yaw),
                north_m=cur.north_m,
                east_m=cur.east_m,
                down_m=cur.down_m,
                vn_mps=cur.vn_mps,
                ve_mps=cur.ve_mps,
                vd_mps=cur.vd_mps,
                gyro_x=float(getattr(msg, "rollspeed", 0.0)),
                gyro_y=float(getattr(msg, "pitchspeed", 0.0)),
                gyro_z=float(getattr(msg, "yawspeed", 0.0)),
                accel_x=cur.accel_x,
                accel_y=cur.accel_y,
                accel_z=cur.accel_z,
                lat_deg=cur.lat_deg,
                lon_deg=cur.lon_deg,
                alt_amsl_m=cur.alt_amsl_m,
                fix_ok=cur.fix_ok,
                hdop=cur.hdop,
                time_boot_ms=boot_ms,
                sensor_stamp_ns=sensor_ns,
            )
            self._have_att = True
        elif t == "LOCAL_POSITION_NED":
            self._latest = FcTelemetry(
                roll_rad=cur.roll_rad,
                pitch_rad=cur.pitch_rad,
                yaw_rad=cur.yaw_rad,
                north_m=float(msg.x),
                east_m=float(msg.y),
                down_m=float(msg.z),
                vn_mps=float(msg.vx),
                ve_mps=float(msg.vy),
                vd_mps=float(msg.vz),
                gyro_x=cur.gyro_x,
                gyro_y=cur.gyro_y,
                gyro_z=cur.gyro_z,
                accel_x=cur.accel_x,
                accel_y=cur.accel_y,
                accel_z=cur.accel_z,
                lat_deg=cur.lat_deg,
                lon_deg=cur.lon_deg,
                alt_amsl_m=cur.alt_amsl_m,
                fix_ok=cur.fix_ok,
                hdop=cur.hdop,
                time_boot_ms=boot_ms,
                sensor_stamp_ns=sensor_ns,
            )
            self._have_pos = True
        elif t == "GPS_RAW_INT":
            fix = int(msg.fix_type) >= 3
            self._latest = FcTelemetry(
                roll_rad=cur.roll_rad,
                pitch_rad=cur.pitch_rad,
                yaw_rad=cur.yaw_rad,
                north_m=cur.north_m,
                east_m=cur.east_m,
                down_m=cur.down_m,
                vn_mps=cur.vn_mps,
                ve_mps=cur.ve_mps,
                vd_mps=cur.vd_mps,
                gyro_x=cur.gyro_x,
                gyro_y=cur.gyro_y,
                gyro_z=cur.gyro_z,
                accel_x=cur.accel_x,
                accel_y=cur.accel_y,
                accel_z=cur.accel_z,
                lat_deg=float(msg.lat) * 1e-7,
                lon_deg=float(msg.lon) * 1e-7,
                alt_amsl_m=float(msg.alt) * 1e-3,
                fix_ok=fix,
                hdop=float(getattr(msg, "eph", 9900)) / 100.0,
                time_boot_ms=boot_ms,
                sensor_stamp_ns=time.monotonic_ns(),
            )
        elif t in ("SCALED_IMU", "SCALED_IMU2", "HIGHRES_IMU"):
            # mG / mrad/s variants — normalize best-effort
            ax = float(getattr(msg, "xacc", 0.0)) * 9.80665 / 1000.0
            ay = float(getattr(msg, "yacc", 0.0)) * 9.80665 / 1000.0
            az = float(getattr(msg, "zacc", 0.0)) * 9.80665 / 1000.0
            gx = float(getattr(msg, "xgyro", 0.0)) / 1000.0
            gy = float(getattr(msg, "ygyro", 0.0)) / 1000.0
            gz = float(getattr(msg, "zgyro", 0.0)) / 1000.0
            self._latest = FcTelemetry(
                roll_rad=cur.roll_rad,
                pitch_rad=cur.pitch_rad,
                yaw_rad=cur.yaw_rad,
                north_m=cur.north_m,
                east_m=cur.east_m,
                down_m=cur.down_m,
                vn_mps=cur.vn_mps,
                ve_mps=cur.ve_mps,
                vd_mps=cur.vd_mps,
                gyro_x=gx,
                gyro_y=gy,
                gyro_z=gz,
                accel_x=ax,
                accel_y=ay,
                accel_z=az,
                lat_deg=cur.lat_deg,
                lon_deg=cur.lon_deg,
                alt_amsl_m=cur.alt_amsl_m,
                fix_ok=cur.fix_ok,
                hdop=cur.hdop,
                time_boot_ms=boot_ms,
                sensor_stamp_ns=sensor_ns,
            )
        else:
            return None
        if not (self._have_att or self._have_pos):
            return None
        return self._latest
