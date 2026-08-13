"""DynamicsBackend — ControlInput in, VehicleState out. UI never imports FDM types."""

from __future__ import annotations

from typing import Protocol

from .dynamics import ArcadeDynamics, PoseState, WingParams
from .sim.vehicle import ControlInput, VehicleState, from_arcade


class DynamicsBackend(Protocol):
    name: str

    def reset(self, *, x: float = 0.0, y: float = 0.0, yaw_deg: float = 0.0, ground_z: float = 0.0) -> None: ...
    def set_params(self, params: WingParams) -> None: ...
    def set_launch_assist(self, on: bool) -> None: ...
    def request_launch(self) -> bool: ...
    def step(self, dt: float, cmd: ControlInput, **kwargs) -> VehicleState: ...
    def vehicle_state(self) -> VehicleState: ...
    def position(self) -> tuple[float, float, float]: ...
    def hpr(self) -> tuple[float, float, float]: ...
    def launch_cue(self) -> str: ...
    def can_launch(self) -> bool: ...


class ArcadeBackend:
    name = "arcade"
    available = True

    def __init__(self, params: WingParams) -> None:
        self.inner = ArcadeDynamics(params)

    @property
    def state(self) -> PoseState:
        return self.inner.state

    @state.setter
    def state(self, value: PoseState) -> None:
        self.inner.state = value

    @property
    def control(self):
        return self.inner.control

    @property
    def params(self) -> WingParams:
        return self.inner.params

    def __getattr__(self, name: str):
        return getattr(self.inner, name)

    def reset(self, *, x: float = 0.0, y: float = 0.0, yaw_deg: float = 0.0, ground_z: float = 0.0) -> None:
        self.inner.reset(x=x, y=y, yaw_deg=yaw_deg, ground_z=ground_z)

    def set_params(self, params: WingParams) -> None:
        self.inner.set_params(params)

    def set_launch_assist(self, on: bool) -> None:
        self.inner.set_launch_assist(on)

    def request_launch(self) -> bool:
        return self.inner.request_launch()

    def vehicle_state(self) -> VehicleState:
        return from_arcade(self.inner.state)

    def step(self, dt: float, cmd: ControlInput | None = None, **kwargs) -> VehicleState:
        if cmd is not None:
            kwargs.setdefault("pitch_cmd", cmd.pitch)
            kwargs.setdefault("roll_cmd", cmd.roll)
            kwargs.setdefault("yaw_cmd", cmd.yaw)
            kwargs.setdefault("throttle_cmd", cmd.throttle)
            kwargs.setdefault("flight_mode", cmd.mode)
        self.inner.step(dt, **kwargs)
        return self.vehicle_state()

    def position(self) -> tuple[float, float, float]:
        return self.inner.position()

    def hpr(self) -> tuple[float, float, float]:
        return self.inner.hpr()

    def launch_cue(self) -> str:
        return self.inner.launch_cue()

    def can_launch(self) -> bool:
        return self.inner.can_launch()


class JSBSimBackend:
    """Named slot. Not a second arcade. JSBSIM-0 lives in studio.sim.jsbsim0 until wired here."""

    name = "jsbsim"
    available = False

    def __init__(self, params: WingParams) -> None:
        self.params = params
        self._reason = "JSBSim backend not wired. Run tests/jsbsim0/run_jsbsim0.py for the headless contract."

    def reset(self, **kwargs) -> None:
        raise RuntimeError(self._reason)

    def set_params(self, params: WingParams) -> None:
        self.params = params

    def set_launch_assist(self, on: bool) -> None:
        return None

    def request_launch(self) -> bool:
        raise RuntimeError(self._reason)

    def step(self, dt: float, cmd: ControlInput | None = None, **kwargs) -> VehicleState:
        raise RuntimeError(self._reason)

    def vehicle_state(self) -> VehicleState:
        raise RuntimeError(self._reason)

    def position(self) -> tuple[float, float, float]:
        raise RuntimeError(self._reason)

    def hpr(self) -> tuple[float, float, float]:
        raise RuntimeError(self._reason)

    def launch_cue(self) -> str:
        return "JSBSIM UNAVAILABLE"

    def can_launch(self) -> bool:
        return False


def make_backend(kind: str, params: WingParams) -> ArcadeBackend:
    key = (kind or "arcade").lower()
    if key == "jsbsim":
        backend = ArcadeBackend(params)
        backend.name = "arcade"
        return backend
    return ArcadeBackend(params)
