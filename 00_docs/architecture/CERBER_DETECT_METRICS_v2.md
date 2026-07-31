# CERBER Detect — Metrics v2 (UAV fine-tune)

**Hub:** [MagistrTheOne/CERBER-CV-v2](https://huggingface.co/MagistrTheOne/CERBER-CV-v2)  
**Collection:** [NULLXES BLACK DEATH (UAV)](https://huggingface.co/collections/MagistrTheOne/nullxes-black-death-uav-6a6c066b4f2f23d31e2a7d56)  
**Run:** `cerber-detect/v1-uav-ft` · **Date:** 2026-07-31  
**Base:** Stage-1 `best.pt` (VisDrone) + Seraphim test → class `uav=2`

## Setup

| Item | Value |
|------|--------|
| Init weights | `cerber-detect/v1/weights/best.pt` |
| Train imgsz | **640** |
| Batch | 64 |
| Epochs | 40 (~0.427 h) |
| Train images | 13568 (VisDrone + Seraphim UAV) |
| Val images | 1800 (548 VisDrone + 1252 UAV) |

## Final validation (`best.pt`)

| Class | Images | Instances | P | R | mAP50 | mAP50-95 |
|-------|--------|-----------|---|---|-------|----------|
| **all** | 1800 | 40043 | 0.816 | 0.655 | **0.709** | **0.419** |
| human | 531 | 13969 | 0.717 | 0.409 | 0.465 | 0.188 |
| vehicle | 546 | 24789 | 0.811 | 0.669 | 0.735 | 0.458 |
| **uav** | 1252 | 1285 | 0.922 | 0.888 | **0.926** | **0.612** |

## vs v1

| | v1 (VisDrone@1280) | v2 (UAV FT@640) |
|--|--------------------|-----------------|
| human mAP50 | 0.672 | 0.465 ↓ |
| vehicle mAP50 | 0.848 | 0.735 ↓ |
| uav mAP50 | — | **0.926** |
| Hub | [CERBER-CV](https://huggingface.co/MagistrTheOne/CERBER-CV) | `CERBER-CV-v2` |

**Use:** v2 when UAV class matters; keep v1 for aerial human/vehicle scene at higher fidelity. Stage 3: re-FT @1280 or longer mix to recover human/vehicle.

## Artifacts

- Weights: `runs/detect/cerber-detect/v1-uav-ft/weights/best.pt`
- Flight ONNX: export separately (do not overwrite v1 `detector_alpha.onnx` without renaming)
