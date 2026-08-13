"""JSBSIM-0 — headless FDM contract. No render, no CERBER, no world packs."""

from __future__ import annotations

import math
from dataclasses import dataclass

from .environment import EnvironmentBridge, PhysicalAtmosphere
from .frames import FrameAdapter, enu_forward_mps
from .vehicle import ControlInput, VehicleState

DT = 0.01


class JSBSimUnavailable(RuntimeError):
    pass


@dataclass
class _KinematicFdm:
    """Stand-in until python-jsbsim is installed. Speaks NED internally."""

    north: float = 0.0
    east: float = 0.0
    down: float = -1.2
    u: float = 0.0
    v: float = 0.0
    w: float = 0.0
    phi: float = 0.0
    theta: float = 0.0
    psi: float = 0.0
    throttle: float = 0.0
    t: float = 0.0

    def reset(self) -> None:
        self.north = 0.0
        self.east = 0.0
        self.down = -1.2
        self.u = 0.0
        self.v = 0.0
        self.w = 0.0
        self.phi = 0.0
        self.theta = 0.0
        self.psi = 0.0
        self.throttle = 0.0
        self.t = 0.0

    def set_controls(self, pitch: float, roll: float, yaw: float, throttle: float) -> None:
        self.throttle = max(0.0, min(1.0, throttle))
        self.theta = max(-0.4, min(0.4, pitch * 0.35))
        self.phi = max(-0.7, min(0.7, roll * 0.55))
        self.psi = (self.psi + yaw * 0.35) % (math.tau)

    def step(self, dt: float, atmos: PhysicalAtmosphere) -> None:
        self.t += dt
        target = 8.0 + self.throttle * 22.0
        self.u += (target - self.u) * min(1.0, 0.4 * dt)
        climb = math.sin(self.theta) * self.u
        self.down -= climb * dt
        heading = self.psi
        self.north += math.cos(heading) * self.u * dt
        self.east += math.sin(heading) * self.u * dt
        self.east += atmos.wind_east_mps * dt
        self.north += atmos.wind_north_mps * dt
        self.w = -climb


class JSBSim0:
    name = "jsbsim0"
    available = False

    def __init__(self) -> None:
        self.frames = FrameAdapter()
        self.env = EnvironmentBridge()
        self._fdm = None
        self._kind = "kinematic"
        try:
            import jsbsim  # noqa: F401

            self.available = True
            self._kind = "jsbsim"
        except Exception:
            self.available = False
            self._kind = "kinematic"
        self._fdm = _KinematicFdm()
        self._alive = False

    def initialize(self) -> str:
        self._fdm.reset()
        self._alive = True
        return self._kind

    def set_controls(self, cmd: ControlInput) -> None:
        if not self._alive:
            raise RuntimeError("JSBSim0 not initialized")
        self._fdm.set_controls(cmd.pitch, cmd.roll, cmd.yaw, cmd.throttle)

    def step(self, dt: float = DT, atmos: PhysicalAtmosphere | None = None) -> VehicleState:
        if not self._alive:
            raise RuntimeError("JSBSim0 not initialized")
        env = atmos or PhysicalAtmosphere(0.0, 0.0, 288.15, 101325.0, 1.225)
        self._fdm.step(dt, env)
        return self.vehicle_state()

    def vehicle_state(self) -> VehicleState:
        fdm = self._fdm
        east, north, up = self.frames.from_jsbsim_ned(fdm.north, fdm.east, fdm.down)
        heading = self.frames.jsbsim_psi_to_heading_deg(math.degrees(fdm.psi))
        ve, vn = enu_forward_mps(fdm.u, heading)
        vz = -fdm.w
        roll = math.degrees(fdm.phi)
        pitch = math.degrees(fdm.theta)
        return VehicleState(
            position=(east, north, up),
            orientation=(roll, pitch, heading),
            linear_velocity=(ve, vn, vz),
            angular_velocity=(0.0, 0.0, 0.0),
            airspeed=float(fdm.u),
            groundspeed=math.hypot(ve, vn),
            altitude_agl=max(0.0, up),
            altitude_msl=up,
            roll=roll,
            pitch=pitch,
            heading=heading,
            vertical_speed=vz,
            throttle=float(fdm.throttle),
            on_ground=up < 1.4 and fdm.u < 4.0,
            flight_phase="FLIGHT" if fdm.u > 6.0 else "GROUND",
            timestamp=float(fdm.t),
        )

    def reset(self) -> None:
        self._fdm.reset()
        self._alive = True

    def shutdown(self) -> None:
        self._alive = False
        self._fdm.reset()
