"""POSEIDON family v3 — naming, SoftBus schemas, VE bank, router VE/VL."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "06_autonomy"))

from poseidon.pack_spec import PackSpecError, load_pack_spec, validate_pack_naming
from poseidon.router import PoseidonRouter, RouterContext, load_router_config
from poseidon.ve.engine import ConceptBank, apply_concept_hit_attrs
from poseidon.vl.scenefact import parse_scenefact_json, validate_scenefact
from soft_bus.messages import (
    TOPIC_POSEIDON_FW_DELTA,
    TOPIC_POSEIDON_VE_HITS,
    TOPIC_POSEIDON_VL_SCENE,
    ConceptHit,
)


def test_naming_reject_hub_brand():
    with pytest.raises(PackSpecError):
        validate_pack_naming("qwen_ve_emb", "POSEIDON-VE-01")
    with pytest.raises(PackSpecError):
        validate_pack_naming("poseidon_ve_emb_2b", "Qwen-VE-01")


def test_ve_vl_fw_packs_load_hub_path():
    for pack in (
        "poseidon_ve_emb_2b",
        "poseidon_ve_rr_2b",
        "poseidon_vl_scenefact_2b",
        "poseidon_fw_gsc",
    ):
        spec = load_pack_spec(
            REPO / "06_autonomy/models/poseidon/packs" / pack / "pack.yaml"
        )
        assert spec.product_name.startswith("POSEIDON-")
        assert spec.load_from_hub is True
        assert spec.base_repo.startswith("Qwen/")
        if pack == "poseidon_fw_gsc":
            assert spec.companion_load is False


def test_cv_packs_have_family_product():
    spec = load_pack_spec(
        REPO / "06_autonomy/models/poseidon/packs/uav_seraphim/pack.yaml"
    )
    assert spec.family == "cv"
    assert spec.product_name == "POSEIDON-CV-UAV-01"


def test_router_ve_on_unknown():
    cfg = load_router_config(
        REPO / "06_autonomy/models/poseidon/router/router.yaml"
    )
    r = PoseidonRouter(
        cfg,
        ["poseidon_ve_emb_2b", "poseidon_ve_rr_2b", "poseidon_vl_scenefact_2b"],
    )
    sel = r.select_ve(
        RouterContext(
            mission_mode="INFRA_INSPECT",
            has_unknown=True,
            unknown_conf=0.4,
        )
    )
    assert "poseidon_ve_emb_2b" in sel


def test_router_fw_off_companion():
    cfg = load_router_config(
        REPO / "06_autonomy/models/poseidon/router/router.yaml"
    )
    assert cfg.futureworld_on_companion is False


def test_concept_bank_topk():
    names = ("smoke", "flame", "cloud_shadow")
    emb = np.eye(3, dtype=np.float32)
    bank = ConceptBank.from_npy_arrays(names, emb)
    ranked = bank.topk(np.array([1.0, 0.0, 0.0], dtype=np.float32), k=2)
    assert ranked[0][0] == "smoke"


def test_apply_concept_hit_attrs():
    hit = ConceptHit(
        object_id="trk-1",
        track_id=1,
        concept="smoke",
        score=0.84,
        model="POSEIDON-VE-01",
    )
    attrs = apply_concept_hit_attrs({}, hit)
    assert attrs["ve_concept"] == "smoke"
    assert attrs["ve_model"] == "POSEIDON-VE-01"


def test_scenefact_parse_and_validate():
    raw = parse_scenefact_json(
        '{"scene_type":"fire_smoke","summary":"smoke near road",'
        '"objects":[{"object_id":"trk-1","role":"subject","concept":"smoke","score":0.9}],'
        '"relations":[],"events":[{"kind":"SEMANTIC_ESCALATION","confidence":0.7}]}'
    )
    assert raw is not None
    sf = validate_scenefact(
        raw, model="POSEIDON-VL-01", trace_id="t1", stamp_ns=1, budget_ms=10.0
    )
    assert sf.validity is True
    assert sf.model == "POSEIDON-VL-01"
    assert sf.scene_type == "fire_smoke"


def test_scenefact_civil_reject():
    sf = validate_scenefact(
        {"scene_type": "nominal", "summary": "weapon sighted", "objects": [], "relations": [], "events": []},
        model="POSEIDON-VL-01",
        trace_id="t",
        stamp_ns=0,
        budget_ms=1.0,
    )
    assert sf.validity is False
    assert "civil_reject" in sf.hallucination_flags


def test_softbus_topics():
    assert TOPIC_POSEIDON_VE_HITS == "/bd/poseidon/ve/hits"
    assert TOPIC_POSEIDON_VL_SCENE == "/bd/poseidon/vl/scene"
    assert TOPIC_POSEIDON_FW_DELTA == "/bd/poseidon/fw/delta"
