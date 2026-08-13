"""AircraftDefinition: visual model is not physics."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class AircraftClass(str, Enum):
    FIXED_WING = "fixed_wing"
    FLYING_WING = "flying_wing"
    VTOL = "vtol"
    MULTIROTOR = "multirotor"
    GROUND_TARGET = "ground_target"
    AIR_TARGET = "air_target"
    CUSTOM = "custom"


PLAYABLE_EGO = {
    AircraftClass.FIXED_WING,
    AircraftClass.FLYING_WING,
    AircraftClass.MULTIROTOR,
    AircraftClass.CUSTOM,
}


@dataclass
class VisualModel:
    path: Path | None = None
    procedural_key: str | None = None
    scale: float = 1.0
    up_axis: str = "Z"
    forward_axis: str = "Y"
    auto_normalize: bool = False
    rotation: tuple[float, float, float] = (0.0, 0.0, 0.0)
    offset: tuple[float, float, float] = (0.0, 0.0, 0.0)


@dataclass
class RotorSpec:
    node: str
    axis: str = "Z"
    direction: float = 1.0


@dataclass
class ControlSurfaceSpec:
    name: str
    node: str
    source: str = "elevator"
    gain: float = 1.0
    axis: str = "Y"
    max_deg: float = 22.0


@dataclass
class AnimationManifest:
    rotors: list[RotorSpec] = field(default_factory=list)
    propellers: list[RotorSpec] = field(default_factory=list)
    control_surfaces: list[ControlSurfaceSpec] = field(default_factory=list)
    flight_clip: str = ""
    hangar_clip: str = ""


@dataclass
class CameraProfile:
    chase_distance: float = 8.0
    chase_height: float = 2.0
    nose_offset: tuple[float, float, float] = (0.0, 0.35, 0.12)


@dataclass
class DemoFlightProfile:
    mass_kg: float = 4.0
    cruise_speed_mps: float = 18.0
    stall_speed_mps: float = 10.0
    max_speed_mps: float = 35.0
    turn_rate_deg: float = 75.0
    is_demo: bool = True


@dataclass
class AircraftMetadata:
    manufacturer: str = ""
    configuration: str = ""
    source: str = "builtin"
    demo_params: bool = True


@dataclass
class AircraftDefinition:
    id: str
    name: str
    class_: AircraftClass
    visual: VisualModel
    camera: CameraProfile = field(default_factory=CameraProfile)
    demo_flight: DemoFlightProfile = field(default_factory=DemoFlightProfile)
    meta: AircraftMetadata = field(default_factory=AircraftMetadata)
    animation: AnimationManifest = field(default_factory=AnimationManifest)
    unconfigured: bool = False
    load_error: str = ""

    @property
    def playable_ego(self) -> bool:
        return self.class_ in PLAYABLE_EGO

    @property
    def class_label(self) -> str:
        return {
            AircraftClass.FIXED_WING: "FIXED WING",
            AircraftClass.FLYING_WING: "FLYING WING",
            AircraftClass.VTOL: "VTOL",
            AircraftClass.MULTIROTOR: "MULTIROTOR",
            AircraftClass.GROUND_TARGET: "GROUND TARGET",
            AircraftClass.AIR_TARGET: "AIR TARGET",
            AircraftClass.CUSTOM: "CUSTOM",
        }[self.class_]
