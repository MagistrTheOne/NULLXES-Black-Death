"""Deterministic static world identity. Replay does not re-simulate the graph."""

from __future__ import annotations

import hashlib
from pathlib import Path

from ..config.paths import STUDIO_ROOT
from ..world_gen.env_packs import scan_packs
from ..world_gen.graph import CACHE_VER

GENERATOR_VERSION = 3
GRAPH_VERSION = int(CACHE_VER)
BACKEND_VERSION = 2
FORMAT_VERSION = 1
FRAME_ID = "blackbox_enu_v1"


def _sha16(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()[:16]


def file_hash(path: Path | None) -> str:
    if path is None or not path.is_file():
        return ""
    return _sha16(path.read_bytes())


def world_pack_hash() -> str:
    acc = hashlib.sha256()
    root = STUDIO_ROOT / "assets" / "world"
    if root.is_dir():
        for path in sorted(root.rglob("pack.yaml")):
            acc.update(path.as_posix().encode("utf-8"))
            acc.update(path.read_bytes())
    for pack in scan_packs():
        for prop in pack.props:
            resolved = pack.resolve(prop)
            acc.update(prop.id.encode("utf-8"))
            acc.update(prop.file.encode("utf-8"))
            if resolved is not None:
                acc.update(file_hash(resolved).encode("utf-8"))
    return acc.hexdigest()[:16]


def aircraft_profile_hash(defn) -> str:
    vis = getattr(defn, "visual", None)
    demo = getattr(defn, "demo_flight", None)
    path = ""
    if vis is not None and vis.path is not None:
        path = str(vis.path)
    blob = "|".join(
        [
            str(getattr(defn, "id", "")),
            str(getattr(defn, "class_", "")),
            path,
            str(getattr(vis, "scale", "")),
            str(getattr(vis, "up_axis", "")),
            str(getattr(demo, "mass_kg", "")),
            str(getattr(demo, "cruise_speed_mps", "")),
            str(getattr(demo, "stall_speed_mps", "")),
            str(getattr(demo, "max_speed_mps", "")),
            str(getattr(demo, "turn_rate_deg", "")),
        ]
    )
    digest = _sha16(blob.encode("utf-8"))
    if vis is not None and vis.path is not None:
        extra = file_hash(vis.path)
        if extra:
            digest = _sha16((digest + extra).encode("utf-8"))
    return digest


def build_contract(
    *,
    seed: int,
    region: str,
    aircraft_id: str,
    profile_hash: str,
    dynamics_backend: str,
    initial_time: str,
    time_flow: str,
) -> dict:
    return {
        "blackbox": {"format_version": FORMAT_VERSION, "frame": FRAME_ID},
        "world": {
            "seed": int(seed),
            "region": region,
            "graph_version": GRAPH_VERSION,
            "generator_version": GENERATOR_VERSION,
        },
        "simulation": {
            "dynamics_backend": dynamics_backend,
            "backend_version": BACKEND_VERSION,
        },
        "aircraft": {"id": aircraft_id, "profile_hash": profile_hash},
        "environment": {"initial_time": initial_time, "time_flow": str(time_flow)},
        "assets": {"world_pack_hash": world_pack_hash()},
    }


def mismatch_reasons(recorded: dict, current: dict) -> list[str]:
    reasons: list[str] = []
    rec_world = recorded.get("world") or {}
    cur_world = current.get("world") or {}
    if int(rec_world.get("seed", 0) or 0) != int(cur_world.get("seed", 0) or 0):
        reasons.append("WORLD SEED MISMATCH")
    if str(rec_world.get("region") or "") != str(cur_world.get("region") or ""):
        reasons.append("REGION MISMATCH")
    if int(rec_world.get("graph_version") or 0) != int(cur_world.get("graph_version") or 0):
        reasons.append("GRAPH VERSION MISMATCH")
    if int(rec_world.get("generator_version") or 0) != int(cur_world.get("generator_version") or 0):
        reasons.append("GENERATOR VERSION MISMATCH")
    rec_ac = recorded.get("aircraft") or {}
    cur_ac = current.get("aircraft") or {}
    if rec_ac.get("profile_hash") and cur_ac.get("profile_hash") and rec_ac.get("profile_hash") != cur_ac.get("profile_hash"):
        reasons.append("AIRCRAFT PROFILE MISMATCH")
    rec_assets = recorded.get("assets") or {}
    cur_assets = current.get("assets") or {}
    if rec_assets.get("world_pack_hash") and cur_assets.get("world_pack_hash"):
        if rec_assets.get("world_pack_hash") != cur_assets.get("world_pack_hash"):
            reasons.append("ASSET VERSION MISMATCH")
    rec_sim = recorded.get("simulation") or {}
    cur_sim = current.get("simulation") or {}
    if rec_sim.get("dynamics_backend") and cur_sim.get("dynamics_backend"):
        if rec_sim.get("dynamics_backend") != cur_sim.get("dynamics_backend"):
            reasons.append("DYNAMICS BACKEND MISMATCH")
    return reasons
