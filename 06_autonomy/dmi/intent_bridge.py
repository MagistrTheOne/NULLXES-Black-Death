"""Map SwarmIntent → GoalMsg fields for existing guidance (not setpoints)."""

from __future__ import annotations

from soft_bus.messages import GoalMsg, PolicyDecisionMsg

from .messages import IntentKind, SwarmIntent
from .mission_policy import MissionPolicyGate

_INTENT_ACTION = {
    IntentKind.LOITER: "LOITER",
    IntentKind.GOTO_XYZ: "GOTO_XYZ",
    IntentKind.EXPLORE_SECTOR: "EXPLORE_SECTOR",
    IntentKind.RTB: "RTB",
}


def intent_to_goal(intent: SwarmIntent, *, stamp_s: float | None = None) -> GoalMsg:
    """Convert mission intent into a planning goal.

    EXPLORE_SECTOR and GOTO_XYZ use intent x,y,z (sector centroid filled by coordinator).
    LOITER keeps horizontal position and uses intent.z as loiter altitude.
    """
    t = stamp_s if stamp_s is not None else intent.stamp_s
    action = _INTENT_ACTION.get(intent.kind, intent.kind.value)
    if intent.kind == IntentKind.LOITER:
        return GoalMsg(
            x=intent.x,
            y=intent.y,
            z=intent.z,
            stamp_s=t,
            trace_id=intent.trace_id,
            action=action,
        )
    if intent.kind in (IntentKind.EXPLORE_SECTOR, IntentKind.GOTO_XYZ, IntentKind.RTB):
        return GoalMsg(
            x=intent.x,
            y=intent.y,
            z=intent.z,
            stamp_s=t,
            trace_id=intent.trace_id,
            action=action,
        )
    raise ValueError(f"unsupported intent kind {intent.kind!r}")


def intent_to_goal_gated(
    intent: SwarmIntent,
    gate: MissionPolicyGate,
    *,
    stamp_s: float | None = None,
) -> tuple[GoalMsg | None, PolicyDecisionMsg]:
    """Policy gate before GoalMsg — deny → (None, decision)."""
    t = stamp_s if stamp_s is not None else intent.stamp_s
    action = _INTENT_ACTION.get(intent.kind, intent.kind.value)
    decision = gate.allow_action(
        action,
        x=intent.x,
        y=intent.y,
        z=intent.z,
        trace_id=intent.trace_id,
        stamp_s=t,
    )
    if not decision.allowed:
        return None, decision
    return intent_to_goal(intent, stamp_s=t), decision
