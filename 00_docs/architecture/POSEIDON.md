# NULLXES POSEIDON

**Status:** LOCKED naming — local specialist agent runtime  
**Not:** chat LLM · cloud agent · Ollama wrapper  
**Is:** edge router + N dataset-trained ONNX packs on NULLXES hardware

```
Camera
   │
   ├─► CERBER (generalist Detect)
   │
   └─► POSEIDON Router
            │
            ├─► pack uav_seraphim     (Seraphim/DUT)
            ├─► pack fire_flame       (FLAME)
            └─► pack power_insplad    (InsPLAD/MPID)
                    │
                    ▼
              cerber_remap → Track → Fusion → DMI WorldFact
```

## Pack contract

Path: `06_autonomy/models/poseidon/packs/<pack_id>/`

| Field | Meaning |
|-------|---------|
| `pack_id` | Stable id |
| `dataset` | Source dataset name |
| `onnx_layout` | Default `yolo_v8_raw` |
| `model_path` | Relative ONNX |
| `sha256` | Fail-closed |
| `cerber_remap` | pack cls → CERBER locked id |
| `budget_ms` | Hard infer budget hint |

## Runtime

Code: `06_autonomy/poseidon/`

- `pack_spec.py` — load/validate
- `session.py` — ORT session
- `router.py` — which packs this frame
- `runtime.py` — step(bgr, ctx)
- `merge.py` — class-aware merge with CERBER

## SoftBus

| Topic | Role |
|-------|------|
| `/bd/poseidon/active_packs` | Active pack ids + latency |
| `/bd/poseidon/detections` | Pre-merge specialist boxes |
| `/bd/vision/detections` | Merged (CERBER + POSEIDON) |

## Civil

ADR-004. No weapon packs. No cloud LLM.

## Refs

- [ADR-005](../adr/ADR-005_POSEIDON.md) · [CERBER_VISION_STACK](./CERBER_VISION_STACK.md) · [CERBER_DATASETS](./CERBER_DATASETS.md)
