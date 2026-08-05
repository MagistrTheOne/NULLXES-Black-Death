---
license: agpl-3.0
library_name: ultralytics
tags: [object-detection, yolov8, aerial, drone, uav, visdrone, seraphim, nullxes, cerber]
pipeline_tag: object-detection
---

# NULLXES CERBER-CV v2 (UAV fine-tune)

Fine-tune of [CERBER-CV](https://huggingface.co/MagistrTheOne/CERBER-CV) with Seraphim drone (`uav`) + VisDrone keep.

## Metrics (val 1800 imgs)

| Class | P | R | mAP50 | mAP50-95 |
|-------|---|---|-------|----------|
| all | 0.816 | 0.655 | 0.709 | 0.419 |
| human | 0.717 | 0.409 | 0.465 | 0.188 |
| vehicle | 0.811 | 0.669 | 0.735 | 0.458 |
| **uav** | 0.922 | 0.888 | **0.926** | **0.612** |

Train: 40 ep @640 from v1 best · ~0.43 h RTX PRO 6000.  
Note: human/vehicle below v1 (prefer v1 for scene-only; v2 when UAV needed).
