# ADR-006 — POSEIDON Family (CV / VE / VL / FW) + Post-FT Naming

**Status:** Accepted  
**Date:** 2026-08-08  
**Deciders:** NULLXES systems architecture  
**Refs:** [ADR-005](ADR-005_POSEIDON.md) · [POSEIDON_VE_VL.md](../architecture/POSEIDON_VE_VL.md) · [MODEL_RELEASE_SPEC.md](../architecture/MODEL_RELEASE_SPEC.md)

## Context

POSEIDON expands beyond CV detect packs into open-vocab embeddings (VE), structured SceneFact (VL), and plan-time WorldDelta (FW). Training bases may come from Hub (Qwen), but product/SoftBus ids must remain POSEIDON-only.

## Decision

1. **Families:** every pack declares `family ∈ {cv, ve, vl, fw}` and `product_name` starting with `POSEIDON-`.
2. **Post-FT naming:** exported pack_id / SoftBus model never use Hub brand strings (`qwen`, `siglip`, `florence`). Hub id lives only in `base_repo`.
3. **CV pack_ids unchanged** (`uav_seraphim`, …) for mission profile compatibility; new packs use `poseidon_*` prefix.
4. **Registry v3** lists family + product_name + wave + channel.
5. **Router v2** adds VE/VL event gates; `futureworld_on_companion: false`.
6. **FW-GSC** (`poseidon_fw_gsc`) is GSC-only bootstrap; not UAV physics; aerial FW is a later `poseidon_fw_*` FT pack.
7. VE/VL/FW outputs stop at ConceptHit / SceneFact / WorldDelta — never GuidanceIntent.

## Consequences

- `06_autonomy/models/poseidon/registry/registry.yaml` version 3.  
- SoftBus topics `/bd/poseidon/ve/hits`, `/bd/poseidon/vl/scene`, `/bd/poseidon/fw/delta`.  
- `validate_registry.py` rejects illegal pack_id / product_name.  
