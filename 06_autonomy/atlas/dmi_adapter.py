"""AllocationPlan → GroundSwarmCoordinator exclusive offers."""

from __future__ import annotations

from dmi.coordinator import GroundSwarmCoordinator
from dmi.messages import TaskOffer

from .messages import AllocationPlan


def apply_plan(coord: GroundSwarmCoordinator, plan: AllocationPlan, *, now_s: float) -> list[TaskOffer]:
    out: list[TaskOffer] = []
    for asg in plan.assignments:
        if asg.intent_kind == "EXPLORE_SECTOR":
            offer = coord.allocate_explore_sector(asg.sector_id, now_s=now_s)
            if offer is not None:
                out.append(offer)
        elif asg.intent_kind == "GOTO_XYZ":
            continue
        elif asg.intent_kind == "LOITER":
            continue
    return out
