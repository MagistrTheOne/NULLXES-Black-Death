"""ArduPlane Guided adapter — SoftBus Goal/Setpoint → Plane MAVLink contracts.

FACT: Plane Guided does not support Copter-style velocity NED position targets.
See: https://ardupilot.org/dev/docs/plane-commands-in-guided-mode.html
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass
from enum import Enum

from soft_bus.messages import GoalMsg, MavlinkHealthMsg, Setpoint


class PlaneCmdKind(str, Enum):
    GOTO_LLA = "GOTO_LLA"  # MISSION_ITEM_INT NAV_WAYPOINT current=2
    ALT_LOCAL_OFFSET = "ALT_LOCAL_OFFSET"  # SET_POSITION_TARGET_LOCAL_NED
    ATTITUDE = "ATTITUDE"  # SET_ATTITUDE_TARGET (continuous)
    LOITER = "LOITER"
    RTL = "RTL"
    HOLD = "HOLD"  # stop guided stream (failsafe)


@dataclass(frozen=True)
class PlaneGuidedCommand:
    kind: PlaneCmdKind
    # LLA for GOTO
    lat_deg: float = 0.0
    lon_deg: float = 0.0
    alt_m: float = 0.0
    alt_frame: int = 3  # MAV_FRAME_GLOBAL_RELATIVE_ALT = 3 (above home when used carefully)
    # Local offset NED altitude command (down positive in NED → negative z = climb)
    alt_offset_up_m: float = 0.0
    # Attitude
    roll_rad: float = 0.0
    pitch_rad: float = 0.0
    yaw_rad: float = 0.0
    thrust_norm: float = 0.0
    stamp_s: float = 0.0
    detail: str = ""


@dataclass
class HomeOrigin:
    """WGS84 home for ENU Goal → LLA goto. Required for GOTO_LLA."""

    lat_deg: float
    lon_deg: float
    alt_amsl_m: float = 0.0


def enu_to_lla(
    east_m: float,
    north_m: float,
    up_m: float,
    home: HomeOrigin,
) -> tuple[float, float, float]:
    """Local ENU meters → approx lat/lon/alt_amsl (small baseline)."""
    meters_per_deg_lat = 111_320.0
    meters_per_deg_lon = 111_320.0 * max(0.2, math.cos(math.radians(home.lat_deg)))
    lat = home.lat_deg + (north_m / meters_per_deg_lat)
    lon = home.lon_deg + (east_m / meters_per_deg_lon)
    alt = home.alt_amsl_m + up_m
    return lat, lon, alt


class ArduPlaneAdapter:
    """Maps SoftBus guidance to ArduPlane Guided commands. No Copter velocity API."""

    def __init__(
        self,
        *,
        home: HomeOrigin | None = None,
        prefer_attitude_stream: bool = False,
        heartbeat_timeout_s: float = 1.5,
    ) -> None:
        self.home = home
        self.prefer_attitude_stream = prefer_attitude_stream
        self.heartbeat_timeout_s = heartbeat_timeout_s
        self._health = MavlinkHealthMsg()
        self._last_cmd: PlaneGuidedCommand | None = None

    @property
    def health(self) -> MavlinkHealthMsg:
        return self._health

    def on_heartbeat(
        self,
        *,
        mode: str,
        armed: bool,
        stamp_s: float | None = None,
    ) -> MavlinkHealthMsg:
        now = stamp_s if stamp_s is not None else time.time()
        guided_ok = mode.upper() == "GUIDED"
        self._health = MavlinkHealthMsg(
            link_ok=True,
            mode=mode,
            armed=armed,
            guided_ok=guided_ok,
            failsafe=False,
            last_heartbeat_s=now,
            stamp_s=now,
        )
        return self._health

    def mark_link_lost(self, stamp_s: float | None = None) -> PlaneGuidedCommand:
        now = stamp_s if stamp_s is not None else time.time()
        self._health = MavlinkHealthMsg(
            link_ok=False,
            mode=self._health.mode,
            armed=self._health.armed,
            guided_ok=False,
            failsafe=True,
            last_heartbeat_s=self._health.last_heartbeat_s,
            stamp_s=now,
        )
        cmd = PlaneGuidedCommand(kind=PlaneCmdKind.HOLD, stamp_s=now, detail="fc_link_lost")
        self._last_cmd = cmd
        return cmd

    def goal_to_command(self, goal: GoalMsg) -> PlaneGuidedCommand:
        now = goal.stamp_s or time.time()
        if not self._health.link_ok:
            return PlaneGuidedCommand(kind=PlaneCmdKind.HOLD, stamp_s=now, detail="no_link")
        if self.home is None:
            # Without home, only altitude offset is safe for Plane local target.
            return PlaneGuidedCommand(
                kind=PlaneCmdKind.ALT_LOCAL_OFFSET,
                alt_offset_up_m=float(goal.z),
                stamp_s=now,
                detail="no_home_alt_only",
            )
        lat, lon, alt = enu_to_lla(goal.x, goal.y, goal.z, self.home)
        cmd = PlaneGuidedCommand(
            kind=PlaneCmdKind.GOTO_LLA,
            lat_deg=lat,
            lon_deg=lon,
            alt_m=alt,
            alt_frame=0,  # AMSL when alt from home AMSL + up
            stamp_s=now,
        )
        self._last_cmd = cmd
        return cmd

    def setpoint_to_attitude(self, sp: Setpoint) -> PlaneGuidedCommand:
        now = sp.stamp_s or time.time()
        if not self._health.link_ok or not self._health.guided_ok:
            return PlaneGuidedCommand(kind=PlaneCmdKind.HOLD, stamp_s=now, detail="not_guided")
        cmd = PlaneGuidedCommand(
            kind=PlaneCmdKind.ATTITUDE,
            roll_rad=sp.roll_rad,
            pitch_rad=sp.pitch_rad,
            yaw_rad=0.0,
            thrust_norm=sp.thrust_norm,
            stamp_s=now,
            detail="attitude_stream",
        )
        self._last_cmd = cmd
        return cmd

    def to_mavlink_dict(self, cmd: PlaneGuidedCommand) -> dict:
        """Structured payload for pymavlink sender / HIL recorder."""
        if cmd.kind == PlaneCmdKind.GOTO_LLA:
            # Plane doc: x = longitude * 1e7, y = latitude * 1e7
            return {
                "type": "MISSION_ITEM_INT",
                "command": 16,  # MAV_CMD_NAV_WAYPOINT
                "current": 2,
                "frame": cmd.alt_frame,
                "x": int(cmd.lon_deg * 1e7),
                "y": int(cmd.lat_deg * 1e7),
                "z": float(cmd.alt_m),
                "lat_deg": cmd.lat_deg,
                "lon_deg": cmd.lon_deg,
            }
        if cmd.kind == PlaneCmdKind.ALT_LOCAL_OFFSET:
            return {
                "type": "SET_POSITION_TARGET_LOCAL_NED",
                "coordinate_frame": 7,  # MAV_FRAME_LOCAL_OFFSET_NED
                "z": float(-cmd.alt_offset_up_m),  # NED down
                "type_mask": 0,  # Plane: other fields unsupported
            }
        if cmd.kind == PlaneCmdKind.ATTITUDE:
            return {
                "type": "SET_ATTITUDE_TARGET",
                "roll": cmd.roll_rad,
                "pitch": cmd.pitch_rad,
                "yaw": cmd.yaw_rad,
                "thrust": cmd.thrust_norm,
            }
        if cmd.kind == PlaneCmdKind.LOITER:
            return {"type": "COMMAND_LONG", "command": 17}  # NAV_LOITER_UNLIM
        if cmd.kind == PlaneCmdKind.RTL:
            return {"type": "COMMAND_LONG", "command": 20}  # NAV_RETURN_TO_LAUNCH
        return {"type": "HOLD", "detail": cmd.detail}
