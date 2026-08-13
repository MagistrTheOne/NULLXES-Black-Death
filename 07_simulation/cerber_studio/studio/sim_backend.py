"""DynamicsBackend — Arcade now, JSBSim later. UI/world/audio stay."""

from __future__ import annotations

from typing import Protocol

from .dynamics import ArcadeDynamics, PoseState, WingParams


class DynamicsBackend(Protocol):
    state: PoseState

    def reset(self, *, x: float = 0.0, y: float = 0.0, yaw_deg: float = 0.0, ground_z: float = 0.0) -> None: ...
    def set_params(self, params: WingParams) -> None: ...
    def set_launch_assist(self, on: bool) -> None: ...
    def request_launch(self) -> bool: ...
    def step(self, dt: float, **kwargs) -> PoseState: ...
    def position(self) -> tuple[float, float, float]: ...
    def hpr(self) -> tuple[float, float, float]: ...
    def launch_cue(self) -> str: ...
    def can_launch(self) -> bool: ...


class ArcadeBackend:
    name = "arcade"

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

    def step(self, dt: float, **kwargs) -> PoseState:
        return self.inner.step(dt, **kwargs)

    def position(self) -> tuple[float, float, float]:
        return self.inner.position()

    def hpr(self) -> tuple[float, float, float]:
        return self.inner.hpr()

    def launch_cue(self) -> str:
        return self.inner.launch_cue()

    def can_launch(self) -> bool:
        return self.inner.can_launch()


class JSBSimBackend(ArcadeBackend):
    """Next backend. Until JSBSim is wired, this is the explicit slot — not a second arcade."""

    name = "jsbsim"

    def __init__(self, params: WingParams) -> None:
        super().__init__(params)
        self.available = False


def make_backend(kind: str, params: WingParams) -> ArcadeBackend:
    key = (kind or "arcade").lower()
    if key == "jsbsim":
        return JSBSimBackend(params)
    return ArcadeBackend(params)
