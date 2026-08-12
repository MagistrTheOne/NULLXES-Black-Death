"""Mission plan YAML loader."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from dmi.messages import IntentKind


@dataclass(frozen=True)
class PlanSector:
    sector_id: str
    x: float
    y: float
    z: float
    xmin: float = 0.0
    xmax: float = 0.0
    ymin: float = 0.0
    ymax: float = 0.0
    spacing_m: float = 40.0


@dataclass(frozen=True)
class PlanStep:
    kind: IntentKind
    sector_id: str = ""
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    task_id: str = ""


@dataclass(frozen=True)
class MissionPlan:
    plan_id: str
    profile_id: str
    home: tuple[float, float, float]
    sectors: list[PlanSector]
    sequence: list[PlanStep]


def load_mission_plan(path: Path) -> MissionPlan:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"invalid mission plan {path}")
    home = raw.get("home") or {}
    sectors: list[PlanSector] = []
    for s in raw.get("sectors") or []:
        sectors.append(
            PlanSector(
                sector_id=str(s["sector_id"]),
                x=float(s["x"]),
                y=float(s["y"]),
                z=float(s["z"]),
                xmin=float(s.get("xmin", 0.0)),
                xmax=float(s.get("xmax", 0.0)),
                ymin=float(s.get("ymin", 0.0)),
                ymax=float(s.get("ymax", 0.0)),
                spacing_m=float(s.get("spacing_m", 40.0)),
            )
        )
    seq: list[PlanStep] = []
    for i, step in enumerate(raw.get("sequence") or []):
        kind = IntentKind(str(step["kind"]))
        seq.append(
            PlanStep(
                kind=kind,
                sector_id=str(step.get("sector_id", "")),
                x=float(step.get("x", 0.0)),
                y=float(step.get("y", 0.0)),
                z=float(step.get("z", 0.0)),
                task_id=str(step.get("task_id", f"step-{i}")),
            )
        )
    return MissionPlan(
        plan_id=str(raw["plan_id"]),
        profile_id=str(raw["profile_id"]),
        home=(float(home.get("x", 0.0)), float(home.get("y", 0.0)), float(home.get("z", 50.0))),
        sectors=sectors,
        sequence=seq,
    )
