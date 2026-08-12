"""ENU waypoint path — capture radius advance."""

from __future__ import annotations

import math
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Waypoint:
    x: float
    y: float
    z: float


@dataclass
class Path:
    waypoints: list[Waypoint] = field(default_factory=list)
    index: int = 0
    capture_m: float = 12.0

    def current(self) -> Waypoint | None:
        if not self.waypoints or self.index >= len(self.waypoints):
            return None
        return self.waypoints[self.index]

    def done(self) -> bool:
        return not self.waypoints or self.index >= len(self.waypoints)

    def advance(self, x: float, y: float, capture_m: float | None = None) -> Waypoint | None:
        rad = self.capture_m if capture_m is None else capture_m
        while self.index < len(self.waypoints):
            wp = self.waypoints[self.index]
            if math.hypot(wp.x - x, wp.y - y) <= rad:
                self.index += 1
                continue
            return wp
        return None
