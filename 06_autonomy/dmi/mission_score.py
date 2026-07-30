"""Mission Score allocation — pure functions for Ground Swarm Coordinator."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MissionScoreWeights:
    w_distance: float = 0.35
    w_soc: float = 0.35
    w_payload: float = 0.15
    w_health: float = 0.15

    def validate(self) -> None:
        total = self.w_distance + self.w_soc + self.w_payload + self.w_health
        if abs(total - 1.0) > 1e-6:
            raise ValueError(f"weights must sum to 1.0, got {total}")


@dataclass(frozen=True)
class AgentScoreInput:
    agent_id: str
    distance_m: float
    soc: float
    payload_frac: float
    health_factor: float


def _clamp01(v: float) -> float:
    return max(0.0, min(1.0, float(v)))


def score_agent(
    inp: AgentScoreInput,
    *,
    max_distance_m: float,
    weights: MissionScoreWeights | None = None,
) -> float:
    """Higher is better. distance/payload penalized when large."""
    w = weights or MissionScoreWeights()
    w.validate()
    if max_distance_m <= 0.0:
        raise ValueError("max_distance_m must be > 0")
    d_hat = _clamp01(inp.distance_m / max_distance_m)
    soc = _clamp01(inp.soc)
    p_hat = _clamp01(inp.payload_frac)
    h = _clamp01(inp.health_factor)
    return (
        w.w_distance * (1.0 - d_hat)
        + w.w_soc * soc
        + w.w_payload * (1.0 - p_hat)
        + w.w_health * h
    )


def select_best_agent(
    candidates: list[AgentScoreInput],
    *,
    max_distance_m: float,
    weights: MissionScoreWeights | None = None,
) -> tuple[str, float] | None:
    """Return (agent_id, score) for the unique best; None if empty."""
    if not candidates:
        return None
    ranked = [
        (score_agent(c, max_distance_m=max_distance_m, weights=weights), c.agent_id)
        for c in candidates
    ]
    ranked.sort(key=lambda t: (-t[0], t[1]))
    best_score, best_id = ranked[0]
    return best_id, best_score
