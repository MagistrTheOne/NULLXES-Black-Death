# POSEIDON Family — CV / VE / VL / FW

**Status:** LOCKED v3 · 2026-08-08  
**Refs:** [ADR-005](../adr/ADR-005_POSEIDON.md) · [ADR-006](../adr/ADR-006_POSEIDON_FAMILY.md) · [POSEIDON.md](POSEIDON.md) · [MODEL_RELEASE_SPEC.md](MODEL_RELEASE_SPEC.md)

## Verdict

POSEIDON = perception family. Output stops at facts. DMI plans. Guidance never reads VL/FW text.

```text
POSEIDON-CV  → detect / seg / attr (ONNX)
POSEIDON-VE  → open-vocab ConceptHit   (Qwen3-VL-Embedding-2B)
POSEIDON-VL  → SceneFact JSON          (Qwen3-VL-2B-Instruct)
POSEIDON-FW  → WorldDelta @ GSC        (Qwen-AgentWorld-35B-A3B)
DMI          → policy / plans
Guidance     → DMI-approved only
```

## Naming lock (post-FT / SoftBus)

| Field | Value |
|-------|--------|
| Product / SoftBus `model` | `POSEIDON-VE-01`, `POSEIDON-VL-01`, … |
| pack_id | `poseidon_ve_emb_2b`, `poseidon_vl_scenefact_2b`, … |
| Hub train base | `base_repo` only — never pack_id |
| Forbidden pack_id | `qwen*`, `siglip*`, `florence*` |

## Production packs (registry v3)

| Product | pack_id | family | base_repo | Runtime |
|---------|---------|--------|-----------|---------|
| POSEIDON-CV-* | `uav_seraphim` / `fire_flame` / `power_insplad` / … | cv | Ultralytics export | ORT |
| **POSEIDON-VE-01** | `poseidon_ve_emb_2b` | ve | [`Qwen/Qwen3-VL-Embedding-2B`](https://huggingface.co/Qwen/Qwen3-VL-Embedding-2B) | `transformers_hub` + `concepts.fp16.npy` |
| **POSEIDON-VE-R01** | `poseidon_ve_rr_2b` | ve | [`Qwen/Qwen3-VL-Reranker-2B`](https://huggingface.co/Qwen/Qwen3-VL-Reranker-2B) | `transformers_hub` |
| **POSEIDON-VL-01** | `poseidon_vl_scenefact_2b` | vl | [`Qwen/Qwen3-VL-2B-Instruct`](https://huggingface.co/Qwen/Qwen3-VL-2B-Instruct) (fallback [`Qwen2-VL-2B-Instruct`](https://huggingface.co/Qwen/Qwen2-VL-2B-Instruct)) | `transformers_hub` |
| **POSEIDON-FW-GSC** | `poseidon_fw_gsc` | fw | [`Qwen/Qwen-AgentWorld-35B-A3B`](https://huggingface.co/Qwen/Qwen-AgentWorld-35B-A3B) | `vllm_gsc` · `companion_load: false` |

`load_from_hub: true` = production load from `base_repo` until ONNX/TRT export; STABLE still requires sha on exported artifact (MODEL_RELEASE_SPEC).

GSC / Studio only (not companion default): Embedding-8B, Reranker-8B, AgentWorld-35B.

## Data path

```text
CAM → CERBER + POSEIDON-CV → TRACK/FUSION → WorldFact
         │
         └─ uncertainty → POSEIDON-VE → ConceptHit → WorldObject.attrs
                              │ margin miss
                              ▼
                         POSEIDON-VL → SceneFact → DMI
DMI candidate actions → POSEIDON-FW-GSC → WorldDelta → DMI → Guidance
```

## SoftBus

| Topic | Payload |
|-------|---------|
| `/bd/poseidon/ve/hits` | `ConceptHitArray` |
| `/bd/poseidon/vl/scene` | `SceneFact` |
| `/bd/poseidon/fw/delta` | `WorldDelta` |

## Code

| Path | Role |
|------|------|
| `06_autonomy/poseidon/ve/` | Embedding + concept bank + attrs merge |
| `06_autonomy/poseidon/vl/` | SceneFact parse/validate + Qwen3-VL infer |
| `06_autonomy/poseidon/fw/` | GSC OpenAI client |
| `06_autonomy/poseidon/semantic.py` | Event-driven VE→RR→VL |
| `06_autonomy/models/poseidon/scripts/build_ve_pack.py` | Bake bank from Embedding-2B |
| `06_autonomy/models/poseidon/scripts/train_vl_scenefact.py` | LoRA → `poseidon_vl_scenefact_2b` |

## Bake / train (real Hub weights)

```bash
# VE bank (POSEIDON-VE-01)
python 06_autonomy/models/poseidon/scripts/build_ve_pack.py \
  --config 06_autonomy/models/poseidon/configs/ve/emb_2b.yaml

# VL LoRA (POSEIDON-VL-01)
python 06_autonomy/models/poseidon/scripts/train_vl_scenefact.py \
  --config 06_autonomy/models/poseidon/configs/vl/scenefact_2b.yaml \
  --data "$POSEIDON_DATA_ROOT/scenefact_civil_v1"
```

FW: set `POSEIDON_FW_GSC_URL=http://gsc:8000/v1` — never companion load.

## Hard rules

1. VE/VL/FW never publish `GuidanceIntent`.
2. Geometry from Track/VIO/Fusion only.
3. AgentWorld ≠ UAV physics; aerial FW = later `poseidon_fw_aerial_v1` on SoftBus traces.
4. Civil reject on concepts / SceneFact / WorldDelta.
5. Fail-closed schema / civil / sha for STABLE.

## KPI

| Layer | Metrics |
|-------|---------|
| CV | mAP / P / R / p95 / sha |
| VE | Open-vocab Recall@k · Concept F1 · p95 · VRAM |
| VL | Schema validity · Hallucination rate · Grounding · p95 |
| FW | Next-state consistency · GSC latency · schema validity |
