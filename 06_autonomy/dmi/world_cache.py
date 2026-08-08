"""Shared World Cache — facts + WorldObjects with TTL (not a SLAM map)."""

from __future__ import annotations

from dataclasses import dataclass, replace

from .messages import WorldFact, WorldObject

DEFAULT_TTL_S = 30.0


@dataclass
class SharedWorldCache:
    ttl_s: float = DEFAULT_TTL_S
    _facts: dict[str, WorldFact] | None = None
    _objects: dict[str, WorldObject] | None = None

    def __post_init__(self) -> None:
        if self.ttl_s <= 0.0:
            raise ValueError("ttl_s must be > 0")
        if self._facts is None:
            self._facts = {}
        if self._objects is None:
            self._objects = {}

    def upsert(self, fact: WorldFact, *, now_s: float) -> bool:
        """Insert or merge fact. Returns True if cache changed."""
        if not (0.0 <= fact.confidence <= 1.0):
            raise ValueError("confidence must be in [0, 1]")
        self.purge(now_s)
        assert self._facts is not None
        old = self._facts.get(fact.fact_id)
        if old is None:
            self._facts[fact.fact_id] = fact
            return True
        if fact.stamp_s > old.stamp_s or (
            fact.stamp_s == old.stamp_s and fact.confidence > old.confidence
        ):
            self._facts[fact.fact_id] = fact
            return True
        return False

    def upsert_object(self, obj: WorldObject, *, now_s: float) -> tuple[bool, WorldObject]:
        """Merge WorldObject by object_id; preserves first_seen_s."""
        if not (0.0 <= obj.confidence <= 1.0):
            raise ValueError("confidence must be in [0, 1]")
        self.purge(now_s)
        assert self._objects is not None
        old = self._objects.get(obj.object_id)
        if old is None:
            stored = replace(
                obj,
                first_seen_s=obj.first_seen_s or obj.last_seen_s or now_s,
                last_seen_s=obj.last_seen_s or now_s,
                state=obj.state or "observed",
            )
            self._objects[obj.object_id] = stored
            return True, stored
        if obj.last_seen_s < old.last_seen_s and obj.confidence <= old.confidence:
            return False, old
        stored = replace(
            obj,
            first_seen_s=old.first_seen_s or obj.first_seen_s or now_s,
            last_seen_s=max(obj.last_seen_s, now_s, old.last_seen_s),
            state="confirmed" if old.state in ("observed", "tentative", "confirmed") else obj.state,
            attrs={**old.attrs, **obj.attrs},
        )
        self._objects[obj.object_id] = stored
        return True, stored

    def purge(self, now_s: float) -> int:
        assert self._facts is not None and self._objects is not None
        dead_f = [fid for fid, f in self._facts.items() if now_s - f.stamp_s > self.ttl_s]
        for fid in dead_f:
            del self._facts[fid]
        dead_o = [
            oid for oid, o in self._objects.items() if now_s - o.last_seen_s > self.ttl_s
        ]
        for oid in dead_o:
            del self._objects[oid]
        return len(dead_f) + len(dead_o)

    def get(self, fact_id: str, *, now_s: float) -> WorldFact | None:
        self.purge(now_s)
        assert self._facts is not None
        return self._facts.get(fact_id)

    def get_object(self, object_id: str, *, now_s: float) -> WorldObject | None:
        self.purge(now_s)
        assert self._objects is not None
        return self._objects.get(object_id)

    def all_facts(self, *, now_s: float) -> list[WorldFact]:
        self.purge(now_s)
        assert self._facts is not None
        return list(self._facts.values())

    def all_objects(self, *, now_s: float) -> list[WorldObject]:
        self.purge(now_s)
        assert self._objects is not None
        return list(self._objects.values())
