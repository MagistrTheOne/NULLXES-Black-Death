"""Soft-bus guidance node.

Publishes setpoint when NAV + (GOAL or TrackTarget) present and channel active.
Track modes: chase / escort / deny — civil presence only (ADR-004).
"""

from __future__ import annotations

import math
import time

from control.guidance.simple_guidance import NavState, simple_guidance
from control.guidance.track_guidance import track_guidance
from soft_bus.bus import SoftBus
from soft_bus.messages import (
    TOPIC_ACTIVE,
    TOPIC_FM_MODE,
    TOPIC_GOAL,
    TOPIC_NAV,
    TOPIC_SETPOINT,
    TOPIC_TRACK_TARGET,
    ActiveChannel,
    FmMode,
    GoalMsg,
    NavStateMsg,
    Setpoint,
    TrackTarget,
)


class GuidanceSoftNode:
    def __init__(self, bus: SoftBus, channel_id: str = "A") -> None:
        self.bus = bus
        self.channel_id = channel_id
        self._nav: NavStateMsg | None = None
        self._goal: GoalMsg | None = None
        self._track: TrackTarget | None = None
        self._mode = "SAFE_LOITER"
        self._active = "A"
        bus.subscribe(TOPIC_NAV, self._on_nav)
        bus.subscribe(TOPIC_GOAL, self._on_goal)
        bus.subscribe(TOPIC_TRACK_TARGET, self._on_track)
        bus.subscribe(TOPIC_FM_MODE, self._on_mode)
        bus.subscribe(TOPIC_ACTIVE, self._on_active)

    def _on_nav(self, m: NavStateMsg) -> None:
        self._nav = m
        self.publish()

    def _on_goal(self, m: GoalMsg) -> None:
        self._goal = m
        self.publish()

    def _on_track(self, m: TrackTarget) -> None:
        self._track = m
        self.publish()

    def _on_mode(self, m: FmMode) -> None:
        self._mode = m.mode
        self.publish()

    def _on_active(self, m: ActiveChannel) -> None:
        self._active = m.channel_id
        self.publish()

    def publish(self) -> None:
        if self._active != self.channel_id:
            return
        if self._nav is None:
            return
        if math.isnan(self._nav.yaw):
            return

        thrust = 0.35
        if self._mode in ("SAFE_LOITER", "RTB"):
            thrust = 0.25
        if self._mode == "DEGRADED_PROP":
            thrust = 0.3

        nav = NavState(
            self._nav.x,
            self._nav.y,
            self._nav.z,
            self._nav.vx,
            self._nav.vy,
            self._nav.vz,
            self._nav.yaw,
        )

        if self._track is not None and self._mode not in ("SAFE_LOITER", "RTB"):
            out = track_guidance(
                nav,
                self._track.x,
                self._track.y,
                self._track.z,
                self._track.mode,
            )
            # Scale thrust for FM modes
            if self._mode in ("SAFE_LOITER", "RTB"):
                pass
            else:
                out = type(out)(
                    out.roll_rad,
                    out.pitch_rad,
                    out.yaw_rate_rps,
                    thrust,
                    out.valid,
                )
        elif self._goal is not None:
            out = simple_guidance(
                nav, self._goal.x, self._goal.y, self._goal.z, thrust
            )
        else:
            return

        key = (
            round(out.roll_rad, 4),
            round(out.pitch_rad, 4),
            round(out.thrust_norm, 4),
            self._mode,
            getattr(self._track, "track_id", -1) if self._track else -1,
        )
        if getattr(self, "_last_key", None) == key:
            return
        self._last_key = key
        self.bus.publish(
            TOPIC_SETPOINT,
            Setpoint(
                out.roll_rad,
                out.pitch_rad,
                out.yaw_rate_rps,
                out.thrust_norm,
                out.valid,
                time.time(),
            ),
        )


def main(bus: SoftBus | None = None, channel_id: str = "A") -> SoftBus:
    bus = bus or SoftBus()
    GuidanceSoftNode(bus, channel_id=channel_id)
    return bus


if __name__ == "__main__":
    main()
    print("guidance soft node ready")
