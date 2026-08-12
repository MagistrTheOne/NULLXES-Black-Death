"""ATLAS planner — STABLE ONNX or Mission Score teacher. Never random."""

from __future__ import annotations

import math
import uuid
from pathlib import Path

from dmi.mission_score import AgentScoreInput, select_best_agent

from .messages import AllocationPlan, Assignment, CopSnapshot
from .runtime import load_onnx_session, pack_is_stable


def _default_pack() -> Path:
    return (
        Path(__file__).resolve().parents[1]
        / "models"
        / "atlas"
        / "packs"
        / "atlas_alloc_v1"
        / "pack.yaml"
    )


class AtlasPlanner:
    def __init__(self, *, pack_yaml: Path | None = None, max_distance_m: float = 500.0) -> None:
        self.pack_yaml = pack_yaml or _default_pack()
        self.max_distance_m = max_distance_m
        self._session = load_onnx_session(self.pack_yaml) if pack_is_stable(self.pack_yaml) else None

    @property
    def using_onnx(self) -> bool:
        return self._session is not None

    def plan(self, snap: CopSnapshot) -> AllocationPlan:
        assignments: list[Assignment] = []
        for sec in snap.sectors:
            if sec.assigned_agent:
                continue
            cands = [
                AgentScoreInput(
                    agent_id=a.agent_id,
                    distance_m=math.hypot(a.x - sec.x, a.y - sec.y),
                    soc=a.soc,
                    payload_frac=a.payload_frac,
                    health_factor=a.health_factor,
                )
                for a in snap.agents
            ]
            best = select_best_agent(cands, max_distance_m=self.max_distance_m)
            if best is None:
                continue
            agent_id, score = best
            assignments.append(
                Assignment(
                    agent_id=agent_id,
                    sector_id=sec.sector_id,
                    intent_kind="EXPLORE_SECTOR",
                    score=score,
                    reason_code="SCORE",
                )
            )
        return AllocationPlan(
            plan_id=str(uuid.uuid4()),
            stamp_s=snap.stamp_s,
            trace_id=snap.trace_id,
            model="BLACK-ATLAS-ALLOC-01" if self._session is None else "BLACK-ATLAS-ALLOC-01-ORT",
            assignments=tuple(assignments),
        )
