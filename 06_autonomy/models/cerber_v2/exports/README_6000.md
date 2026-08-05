# RTX PRO 6000 Blackwell — CERBER Detect packs

## Runs (same layout as v2-pursuit-2080)
- `runs/detect/cerber-detect/v1-rtx6000-blackwell`
- `runs/detect/cerber-detect/v2-rtx6000-blackwell`
- `runs/detect/cerber-detect/v2-pursuit-2080` (local FT)

## Exports
- `exports/rtx6000_blackwell_v1` — HF results.png + local val plots
- `exports/rtx6000_blackwell_v2` — HF results.png/csv + curves + local val plots

## Local re-val on VisDrone val=548 (this machine, weights from 6000 train)
| | P | R | mAP50 | mAP50-95 | imgsz |
|--|--:|--:|--:|--:|--:|
| v1 | 0.819 | 0.693 | 0.762 | 0.442 | 1280 |
| v2 | 0.749 | 0.549 | 0.603 | 0.325 | 640 |
| 2080 FT | 0.757 | 0.555 | 0.608 | 0.328 | 640 |

Note: v2 canon all-mAP50 0.709 includes UAV val (1800). Local re-val is VisDrone-only → scene metrics drop vs UAV-boosted all-score.
