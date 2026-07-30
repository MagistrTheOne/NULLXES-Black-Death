"""Map SwarmIntent → GoalMsg fields for existing guidance (not setpoints)."""

from __future__ import annotations

from soft_bus.messages import GoalMsg

from .messages import IntentKind, SwarmIntent


def intent_to_goal(intent: SwarmIntent, *, stamp_s: float | None = None) -> GoalMsg:
    """Convert mission intent into a planning goal.

    EXPLORE_SECTOR and GOTO_XYZ use intent x,y,z (sector centroid filled by coordinator).
    LOITER keeps horizontal position and uses intent.z as loiter altitude.
    """
    t = stamp_s if stamp_s is not None else intent.stamp_s
    if intent.kind == IntentKind.LOITER:
        return GoalMsg(x=intent.x, y=intent.y, z=intent.z, stamp_s=t)
    if intent.kind in (IntentKind.EXPLORE_SECTOR, IntentKind.GOTO_XYZ):
        return GoalMsg(x=intent.x, y=intent.y, z=intent.z, stamp_s=t)
    raise ValueError(f"unsupported intent kind {intent.kind!r}")
