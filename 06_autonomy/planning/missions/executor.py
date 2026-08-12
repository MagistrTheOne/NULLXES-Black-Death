"""GSC mission executor — sequential allocate via GroundSwarmCoordinator."""

from __future__ import annotations

from dmi.coordinator import GroundSwarmCoordinator
from dmi.messages import IntentKind, Sector, TaskClaim, TaskOffer
from .plan import MissionPlan, PlanStep


class MissionExecutor:
    def __init__(self, coord: GroundSwarmCoordinator, plan: MissionPlan) -> None:
        self.coord = coord
        self.plan = plan
        self.index = 0
        self.last_offer: TaskOffer | None = None
        for s in plan.sectors:
            coord.upsert_sector(
                Sector(
                    s.sector_id,
                    s.x,
                    s.y,
                    s.z,
                    xmin=s.xmin,
                    xmax=s.xmax,
                    ymin=s.ymin,
                    ymax=s.ymax,
                    spacing_m=s.spacing_m,
                )
            )

    def done(self) -> bool:
        return self.index >= len(self.plan.sequence)

    def _allocate_step(self, step: PlanStep, *, now_s: float) -> TaskOffer | None:
        if step.kind == IntentKind.EXPLORE_SECTOR:
            return self.coord.allocate_explore_sector(step.sector_id, now_s=now_s)
        if step.kind == IntentKind.GOTO_XYZ:
            return self.coord.allocate_goto(
                step.x, step.y, step.z, task_id=step.task_id or "goto", now_s=now_s
            )
        if step.kind == IntentKind.LOITER:
            return self.coord.allocate_loiter(
                step.x, step.y, step.z, task_id=step.task_id or "loiter", now_s=now_s
            )
        if step.kind == IntentKind.RTB:
            hx, hy, hz = self.plan.home
            return self.coord.allocate_goto(
                hx, hy, hz, task_id=step.task_id or "rtb", now_s=now_s
            )
        return None

    def tick(self, *, now_s: float) -> TaskOffer | None:
        self.coord.expire_offer(now_s=now_s)
        if self.done():
            return None
        if self.coord._open_offer is not None:
            return None
        step = self.plan.sequence[self.index]
        offer = self._allocate_step(step, now_s=now_s)
        self.last_offer = offer
        return offer

    def on_claim(self, claim: TaskClaim, *, now_s: float) -> bool:
        ok = self.coord.on_claim(claim, now_s=now_s)
        if not ok:
            return False
        if claim.kind.value == "ACCEPT":
            self.index += 1
        return True
