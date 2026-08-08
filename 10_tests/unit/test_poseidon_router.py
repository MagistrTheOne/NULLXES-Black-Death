"""POSEIDON router + pack_spec unit tests."""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "06_autonomy"))

from poseidon.pack_spec import load_pack_spec
from poseidon.router import PoseidonRouter, RouterConfig, RouterContext


def test_load_uav_pack_manifest_pending():
    yaml_path = (
        REPO
        / "06_autonomy"
        / "models"
        / "poseidon"
        / "packs"
        / "uav_seraphim"
        / "pack.yaml"
    )
    spec = load_pack_spec(yaml_path, verify_sha=True)
    assert spec.pack_id == "uav_seraphim"
    assert spec.cerber_remap[0] == 2


def test_router_airspace_guard_enables_uav():
    cfg = RouterConfig(
        max_packs_per_frame=1,
        priority=("uav_seraphim", "fire_flame"),
        gates={
            "uav_seraphim": {
                "mission_modes": ["AIRSPACE_GUARD", "NOMINAL"],
                "cerber_hint_cls": [2],
                "cerber_hint_min_conf": 0.15,
            }
        },
    )
    r = PoseidonRouter(cfg, ["uav_seraphim", "fire_flame"])
    sel = r.select(RouterContext(mission_mode="AIRSPACE_GUARD"))
    assert sel == ["uav_seraphim"]


def test_router_nominal_needs_hint():
    cfg = RouterConfig(
        max_packs_per_frame=1,
        priority=("uav_seraphim",),
        gates={
            "uav_seraphim": {
                "mission_modes": ["NOMINAL"],
                "cerber_hint_cls": [2],
                "cerber_hint_min_conf": 0.15,
            }
        },
    )
    r = PoseidonRouter(cfg, ["uav_seraphim"])
    assert r.select(RouterContext(mission_mode="NOMINAL")) == []
    assert r.select(
        RouterContext(
            mission_mode="NOMINAL",
            cerber_cls_ids=[2],
            cerber_max_conf={2: 0.4},
        )
    ) == ["uav_seraphim"]
