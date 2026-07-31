# CERBER Detect — Datasets

**Status:** [CERBER_STATUS.md](./CERBER_STATUS.md) · stack notes: `06_autonomy/models/datasets/DATASET_STACK_A100.md`

## Used in v1 (CERBER-CV)

| Dataset | Role | Classes mapped | Source |
|---------|------|----------------|--------|
| **VisDrone-DET** | train + val | pedestrian/people → `human`; bike…motor → `vehicle` | Ultralytics auto + [VisDrone-Dataset](https://github.com/VisDrone/VisDrone-Dataset) Task 1 |

Splits on disk (CERBER tree): `images/{train,val}`, `labels/{train,val}` under prepare root (pod: `/workspace/datasets/cerber`).

VisDrone Task 1 sizes (upstream): train ~1.44 GB, val ~0.07 GB, test-dev ~0.28 GB (GT available). We trained on Ultralytics train/val convert; test-dev optional for extra bench.

## Planned / not in v1

| Dataset | Target CERBER class | Status |
|---------|---------------------|--------|
| UETT4K Anti-UAV | `uav` | **Not on HF.** Full dump via SharePoint from [GitHub README](https://github.com/mugheessarwarawan/UETT4K-Anti-UAV) |
| Seraphim drone YOLO (HF) | `uav` alt | Optional: `lgrzybowski/seraphim-drone-detection-dataset` |
| UAVDT | vehicle / aerial | DatasetNinja / manual |
| DOTA | infrastructure / building / … | DatasetNinja / OBB→axis later |
| Custom (own airframe) | landing_zone, cargo, fire, … | Stage 2+ capture |

## Remap

Rules: `06_autonomy/models/datasets/remap_rules.yaml`  
Prepare: `06_autonomy/models/scripts/prepare_cerber_data.py`

## Civil constraint

Civil infrastructure / public aerial benchmarks only. No weapons / targeting datasets.
