"""COP merge — OBSERVED_BY / ASSIGNED_TO by object_id (best-effort, TTL not a SLAM map)."""

from __future__ import annotations

from dmi.messages import Relation, WorldObject
from dmi.world_cache import SharedWorldCache


def merge_relation(cache: SharedWorldCache, rel: Relation, *, now_s: float) -> None:
    """Relations are not WorldObjects; stash as attrs on subject if present."""
    obj = cache.get_object(rel.subject_id, now_s=now_s)
    if obj is None:
        return
    attrs = dict(obj.attrs)
    attrs[rel.kind.lower()] = rel.object_id
    from dataclasses import replace

    cache.upsert_object(replace(obj, attrs=attrs, last_seen_s=now_s), now_s=now_s)
