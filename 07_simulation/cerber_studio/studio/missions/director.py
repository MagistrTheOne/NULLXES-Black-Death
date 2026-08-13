"""OperationDirector — YAML trigger/condition/action. No per-mission Python class."""

from __future__ import annotations

from dataclasses import dataclass, field

from .registry import MissionDefinition


@dataclass
class ObjectiveState:
    type: str
    done: bool = False
    elapsed: float = 0.0
    payload: dict = field(default_factory=dict)


class OperationDirector:
    def __init__(self) -> None:
        self.mission: MissionDefinition | None = None
        self.objectives: list[ObjectiveState] = []
        self.success = False
        self.failed = False
        self.unlock: str = ""
        self.grade: dict = {}

    def load(self, mission: MissionDefinition) -> None:
        self.mission = mission
        self.success = False
        self.failed = False
        self.unlock = ""
        self.grade = {}
        specs = mission.objectives or []
        self.objectives = []
        for spec in specs:
            if isinstance(spec, dict):
                kind = str(spec.get("type") or spec.get("kind") or "goto")
                self.objectives.append(ObjectiveState(type=kind, payload=dict(spec)))
            else:
                self.objectives.append(ObjectiveState(type=str(spec)))
        if not self.objectives:
            self.objectives = [ObjectiveState(type="launch"), ObjectiveState(type="land")]
        self.unlock = str(mission.unlock or "")

    def update(
        self,
        dt: float,
        *,
        phase: str,
        agl: float,
        speed: float,
        dist_target: float | None,
        track_id: int | None,
        landing_grade: str,
        assist: bool,
        vz: float,
        on_runway: bool,
    ) -> None:
        if self.success or self.failed or not self.objectives:
            return
        cur = next((o for o in self.objectives if not o.done), None)
        if cur is None:
            self.success = True
            return
        kind = cur.type
        if kind == "launch" and phase in ("LAUNCH", "AIRBORNE", "FLIGHT"):
            cur.done = True
        elif kind in ("reach_zone", "goto"):
            if dist_target is not None and dist_target < 80.0:
                cur.done = True
            if phase in ("FLIGHT", "APPROACH") and agl > 40.0:
                cur.elapsed += dt
                if cur.elapsed > 12.0:
                    cur.done = True
        elif kind in ("acquire_target",):
            if track_id is not None:
                cur.done = True
        elif kind in ("maintain_track",):
            if track_id is not None:
                cur.elapsed += dt
                if cur.elapsed >= float(cur.payload.get("duration_s", 30.0)):
                    cur.done = True
            else:
                cur.elapsed = max(0.0, cur.elapsed - dt * 0.5)
        elif kind in ("return",):
            if on_runway and agl < 40.0:
                cur.done = True
        elif kind == "land" and phase in ("STOPPED", "GROUND_ROLL"):
            cur.done = True
            self.grade = {
                "approach": landing_grade or "—",
                "touchdown_ms": abs(vz),
                "assist": "ON" if assist else "OFF",
            }
        if all(o.done for o in self.objectives):
            self.success = True
            if self.mission:
                if self.mission.unlock:
                    self.unlock = self.mission.unlock
                elif self.mission.id == "target_follow":
                    self.unlock = "night_watch"

    def label(self) -> str:
        if self.success:
            return "OPERATION COMPLETE"
        if not self.objectives:
            return ""
        done = sum(1 for o in self.objectives if o.done)
        cur = next((o for o in self.objectives if not o.done), None)
        name = cur.type.upper().replace("_", " ") if cur else "DONE"
        return f"{done + 1:02d}/{len(self.objectives)}  {name}"
