# POSEIDON packs

Local specialist agents. Canon: `00_docs/architecture/POSEIDON.md` · `POSEIDON_VE_VL.md` · ADR-005 · ADR-006.

## Naming lock (post-FT)

| Field | Rule |
|-------|------|
| `pack_id` / SoftBus `model` / `product_name` | **POSEIDON-*** / `poseidon_*` only |
| Hub upstream | `base_repo` in pack.yaml only |
| Forbidden as pack_id | `qwen*`, `siglip*`, `florence*` |

## Family matrix

| Family | Product | pack_id | Role |
|--------|---------|---------|------|
| **cv** | POSEIDON-CV-UAV-01 | `uav_seraphim` | Detect UAV → CERBER `2` |
| **cv** | POSEIDON-CV-FIRE-01 | `fire_flame` | Fire → `10` |
| **cv** | POSEIDON-CV-POWER-01 | `power_insplad` | Power line → `5` |
| **cv** | POSEIDON-CV-SCENESEG-01 | `scene_segformer_b0` | Scene seg |
| **cv** | POSEIDON-CV-VEHICLEATTR-01 | `vehicle_attr_lowagl` | Low-AGL attrs |
| **ve** | POSEIDON-VE-01 | `poseidon_ve_emb_2b` | Open-vocab ConceptHit |
| **ve** | POSEIDON-VE-R01 | `poseidon_ve_rr_2b` | Concept rerank |
| **vl** | POSEIDON-VL-01 | `poseidon_vl_scenefact_2b` | SceneFact (async) |
| **fw** | POSEIDON-FW-GSC | `poseidon_fw_gsc` | WorldDelta GSC only |

Export on NULLXES GPU servers → fill artifacts + `sha256`. Civil only (ADR-004).

**Train:** [TRAIN.md](./TRAIN.md) · **Registry:** [registry/registry.yaml](./registry/registry.yaml)
