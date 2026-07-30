"""Shared World Cache — best-effort facts with TTL (not a SLAM map)."""

from __future__ import annotations

from dataclasses import dataclass

from .messages import WorldFact

DEFAULT_TTL_S = 30.0


@dataclass
class SharedWorldCache:
    ttl_s: float = DEFAULT_TTL_S
    _facts: dict[str, WorldFact] | None = None

    def __post_init__(self) -> None:
        if self.ttl_s <= 0.0:
            raise ValueError("ttl_s must be > 0")
        if self._facts is None:
            self._facts = {}

    def upsert(self, fact: WorldFact, *, now_s: float) -> bool:
        """Insert or merge. Returns True if cache changed."""
        if not (0.0 <= fact.confidence <= 1.0):
            raise ValueError("confidence must be in [0, 1]")
        self.purge(now_s)
        assert self._facts is not None
        old = self._facts.get(fact.fact_id)
        if old is None:
            self._facts[fact.fact_id] = fact
            return True
        # Prefer fresher; if same stamp, higher confidence wins
        if fact.stamp_s > old.stamp_s or (
            fact.stamp_s == old.stamp_s and fact.confidence > old.confidence
        ):
            self._facts[fact.fact_id] = fact
            return True
        return False

    def purge(self, now_s: float) -> int:
        assert self._facts is not None
        dead = [
            fid
            for fid, f in self._facts.items()
            if now_s - f.stamp_s > self.ttl_s
        ]
        for fid in dead:
            del self._facts[fid]
        return len(dead)

    def get(self, fact_id: str, *, now_s: float) -> WorldFact | None:
        self.purge(now_s)
        assert self._facts is not None
        return self._facts.get(fact_id)

    def all_facts(self, *, now_s: float) -> list[WorldFact]:
        self.purge(now_s)
        assert self._facts is not None
        return list(self._facts.values())
