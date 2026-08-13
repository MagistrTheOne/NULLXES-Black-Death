"""Simulator events — physics / sim / autonomy. HUD must show them."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class EventKind(str, Enum):
    STALL = "STALL"
    OVERSPEED = "OVERSPEED"
    CRASH = "CRASH"
    EXCESSIVE_BANK = "EXCESSIVE_BANK"
    LOW_ALTITUDE = "LOW_ALTITUDE"
    OUT_OF_BOUNDS = "OUT_OF_BOUNDS"
    MISSION_TIMEOUT = "MISSION_TIMEOUT"
    SENSOR_DROPOUT = "SENSOR_DROPOUT"
    LOST_TARGET = "LOST_TARGET"
    FOLLOW_ABORT = "FOLLOW_ABORT"
    LAUNCH = "LAUNCH"
    WAYPOINT = "WAYPOINT"


class EventLayer(str, Enum):
    PHYSICS = "physics"
    SIMULATOR = "simulator"
    AUTONOMY = "autonomy"


LAYER_OF: dict[EventKind, EventLayer] = {
    EventKind.STALL: EventLayer.PHYSICS,
    EventKind.OVERSPEED: EventLayer.PHYSICS,
    EventKind.CRASH: EventLayer.PHYSICS,
    EventKind.EXCESSIVE_BANK: EventLayer.PHYSICS,
    EventKind.LOW_ALTITUDE: EventLayer.PHYSICS,
    EventKind.OUT_OF_BOUNDS: EventLayer.SIMULATOR,
    EventKind.MISSION_TIMEOUT: EventLayer.SIMULATOR,
    EventKind.SENSOR_DROPOUT: EventLayer.SIMULATOR,
    EventKind.LOST_TARGET: EventLayer.AUTONOMY,
    EventKind.FOLLOW_ABORT: EventLayer.AUTONOMY,
    EventKind.LAUNCH: EventLayer.SIMULATOR,
    EventKind.WAYPOINT: EventLayer.AUTONOMY,
}


@dataclass(frozen=True)
class SimEvent:
    kind: EventKind
    t: float
    detail: str = ""

    @property
    def layer(self) -> EventLayer:
        return LAYER_OF[self.kind]

    def as_dict(self) -> dict:
        return {
            "kind": self.kind.value,
            "layer": self.layer.value,
            "t": self.t,
            "detail": self.detail,
        }
