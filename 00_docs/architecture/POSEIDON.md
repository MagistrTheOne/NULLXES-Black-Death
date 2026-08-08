# NULLXES POSEIDON

**Status:** LOCKED naming — local specialist agent runtime (CV / VE / VL / FW)  
**Not:** chat LLM · cloud agent · Ollama wrapper · Hub brand in product ids  
**Is:** edge router + dataset-trained packs on NULLXES hardware

```
Camera
   │
   ├─► CERBER (generalist Detect)
   │
   └─► POSEIDON Router
            │
            ├─► CV  uav_seraphim / fire_flame / power_insplad / …
            ├─► VE  poseidon_ve_emb_2b (+ rr)     → ConceptHit
            ├─► VL  poseidon_vl_scenefact_2b      → SceneFact (async)
            └─► FW  poseidon_fw_gsc (GSC only)    → WorldDelta
                    │
                    ▼
              Track / Fusion → WorldFact → DMI → Guidance
```

## Naming lock

| Field | Rule |
|-------|------|
| `pack_id` / SoftBus `model` / `product_name` | `poseidon_*` / `POSEIDON-*` |
| Hub train base | `base_repo` only |
| Forbidden pack_id | `qwen*`, `siglip*`, `florence*` |

## Pack contract

Path: `06_autonomy/models/poseidon/packs/<pack_id>/`

| Field | Meaning |
|-------|---------|
| `pack_id` | Stable id |
| `family` | `cv` \| `ve` \| `vl` \| `fw` |
| `product_name` | e.g. `POSEIDON-VE-01` |
| `dataset` | Source dataset name |
| `onnx_layout` | `yolo_v8_raw` / `segformer_b0` / `attr_classifier` / `qwen_vl_emb` / `qwen_vl_rr` / `qwen_vl` |
| `base_repo` | Hub provenance (VE/VL/FW) |
| `model_path` | Relative artifact |
| `sha256` | Fail-closed |
| `cerber_remap` | pack cls → CERBER locked id (CV detect) |
| `companion_load` | `false` for FW-GSC |
| `budget_ms` | Hard infer budget hint |

## Runtime

Code: `06_autonomy/poseidon/`

- `pack_spec.py` — load/validate  
- `session.py` — ORT session (CV)  
- `router.py` — CV + VE/VL gates  
- `runtime.py` — CV step  
- `ve/` · `vl/` · `fw/` — semantic / predictive modules  
- `merge.py` — class-aware merge with CERBER  

## SoftBus

| Topic | Role |
|-------|------|
| `/bd/poseidon/active_packs` | Active pack ids + latency |
| `/bd/poseidon/detections` | Pre-merge specialist boxes |
| `/bd/poseidon/ve/hits` | ConceptHit[] |
| `/bd/poseidon/vl/scene` | SceneFact |
| `/bd/poseidon/fw/delta` | WorldDelta (GSC) |
| `/bd/vision/detections` | Merged (CERBER + POSEIDON-CV) |

## Civil

ADR-004. No weapon packs. No cloud LLM. VE/VL/FW never publish GuidanceIntent.

## Refs

- [ADR-005](../adr/ADR-005_POSEIDON.md) · [ADR-006](../adr/ADR-006_POSEIDON_FAMILY.md) · [POSEIDON_VE_VL](./POSEIDON_VE_VL.md) · [CERBER_VISION_STACK](./CERBER_VISION_STACK.md)
