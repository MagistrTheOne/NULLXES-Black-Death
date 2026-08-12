"""SwarmIntent / GoalMsg → current GoalMsg along a Path."""

from __future__ import annotations

from dmi.messages import IntentKind, SwarmIntent
from soft_bus.messages import GoalMsg, NavStateMsg

from .path import Path, Waypoint
from .sector_explore import lawnmower


class TrajectoryPlanner:
    def __init__(self, *, capture_m: float = 12.0, default_half_m: float = 80.0) -> None:
        self.capture_m = capture_m
        self.default_half_m = default_half_m
        self._path: Path | None = None
        self._intent_id = ""
        self._loiter: Waypoint | None = None

    def set_intent(self, intent: SwarmIntent) -> None:
        self._intent_id = intent.intent_id
        self._loiter = None
        if intent.kind == IntentKind.LOITER:
            self._path = Path([Waypoint(intent.x, intent.y, intent.z)], capture_m=self.capture_m)
            self._loiter = Waypoint(intent.x, intent.y, intent.z)
            return
        if intent.kind == IntentKind.GOTO_XYZ:
            self._path = Path([Waypoint(intent.x, intent.y, intent.z)], capture_m=self.capture_m)
            return
        if intent.kind == IntentKind.EXPLORE_SECTOR:
            xmin, xmax = intent.xmin, intent.xmax
            ymin, ymax = intent.ymin, intent.ymax
            if xmax <= xmin or ymax <= ymin:
                h = self.default_half_m
                xmin, xmax = intent.x - h, intent.x + h
                ymin, ymax = intent.y - h, intent.y + h
            spacing = intent.spacing_m if intent.spacing_m > 0 else 40.0
            wps = lawnmower(
                xmin=xmin, xmax=xmax, ymin=ymin, ymax=ymax, z=intent.z, spacing_m=spacing
            )
            self._path = Path(wps, capture_m=self.capture_m)
            return
        if intent.kind == IntentKind.RTB:
            self._path = Path([Waypoint(intent.x, intent.y, intent.z)], capture_m=self.capture_m)
            return
        self._path = Path([Waypoint(intent.x, intent.y, intent.z)], capture_m=self.capture_m)

    def tick(self, nav: NavStateMsg, *, stamp_s: float, trace_id: str = "") -> GoalMsg | None:
        if self._loiter is not None:
            return GoalMsg(
                x=nav.x,
                y=nav.y,
                z=self._loiter.z,
                stamp_s=stamp_s,
                trace_id=trace_id,
                action="LOITER",
            )
        if self._path is None:
            return None
        wp = self._path.advance(nav.x, nav.y)
        if wp is None:
            last = self._path.waypoints[-1] if self._path.waypoints else None
            if last is None:
                return None
            wp = last
        return GoalMsg(
            x=wp.x,
            y=wp.y,
            z=wp.z,
            stamp_s=stamp_s,
            trace_id=trace_id,
            action="GOTO_XYZ",
        )
