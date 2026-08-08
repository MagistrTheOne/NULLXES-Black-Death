# MODEL_RELEASE_SPEC — POSEIDON / CERBER lifecycle

**Status:** Canon v1 · 2026-08-08  
**Refs:** [ADR-005](../adr/ADR-005_POSEIDON.md) · [POSEIDON.md](POSEIDON.md) · `06_autonomy/models/poseidon/`

## Philosophy

Package / release / deploy for **physical autonomy** (Palantir-like), not cloud LLM catalogs. Companion loads only **approved + signed** artifacts.

## ModelPack fields

| Field | Required | Notes |
|-------|----------|-------|
| `pack_id` | yes | Stable id |
| `version` | yes | semver or `vN` |
| `model_path` | yes | Relative ONNX |
| `sha256` | yes | Fail-closed if pending when `release_channel=STABLE` |
| `dataset` | yes | Name |
| `dataset_hash` | recommend | Content hash or manifest id |
| `classes` | yes | Pack classes |
| `cerber_remap` | yes for detect | Locked CERBER ids |
| `onnx_layout` | yes | `yolo_v8_raw` or future ADR |
| `runtime` | yes | `ort` \| `trt` |
| `precision` | yes | `fp32` \| `fp16` \| `int8` |
| `input_size` | yes | `[H,W]` |
| `hardware_target` | recommend | e.g. `orin_nx_16` \| `x86_cuda` |
| `benchmark` | recommend | `{p95_ms, fps_mean, nvpmodel}` |
| `validation_status` | yes | `pending` \| `passed` \| `failed` |
| `release_channel` | yes | `CANDIDATE` \| `STABLE` |
| `approved_by` | STABLE only | Engineer id |
| `created_at` | yes | ISO-8601 |
| `signature` | STABLE only | HMAC/sha placeholder until PKI ADR |

## Pipeline

```text
TRAIN → EXPORT → BENCHMARK → VALIDATE → SIGN → RELEASE → DEPLOY → ROLLBACK
```

| Step | Owner | Gate |
|------|-------|------|
| TRAIN | GPU farm | civil dataset only |
| EXPORT | `export_pack.py` | ONNX + sha |
| BENCHMARK | Orin / target | tegrastats harness |
| VALIDATE | `validate_registry.py` | remap + civil_reject |
| SIGN | release engineer | signature + approved_by |
| RELEASE | registry | channel STABLE or CANDIDATE |
| DEPLOY | companion image | load STABLE only by default |
| ROLLBACK | ops | pin previous sha |

## Channels

| Channel | Flight load default |
|---------|---------------------|
| `CANDIDATE` | Bench / Studio A/B only |
| `STABLE` | Companion flight image |

A/B compare (recorded stream):

| Metric | STABLE | CANDIDATE |
|--------|--------|-----------|
| Recall / mAP | … | … |
| ID switches | … | … |
| Fact p95 | … | … |
| False alerts | … | … |

Promotion: CANDIDATE → STABLE only after acceptance gate documented in pack `benchmark` + `validation_status=passed`.

## Fail-closed

- Missing ONNX + `required: true` → BLOCKED  
- sha mismatch → BLOCKED  
- `release_channel=STABLE` with `sha256=pending` → BLOCKED  
- civil_reject substring in pack_id/dataset → BLOCKED  
- Companion env `POSEIDON_ALLOW_CANDIDATE=0` (default) skips CANDIDATE packs
