---
license: agpl-3.0
library_name: ultralytics
tags:
  - object-detection
  - yolo
  - yolov8
  - aerial
  - drone
  - visdrone
  - onnx
  - nullxes
  - cerber
pipeline_tag: object-detection
---

# NULLXES CERBER-CV (v1)

Civil aerial **scene detector** for the NULLXES CERBER perception stack.  
YOLOv8s fine-tuned on VisDrone-DET with CERBER class remap.

## Metrics (VisDrone val, 548 images)

| Class   | P     | R     | mAP50 | mAP50-95 |
|---------|-------|-------|-------|----------|
| all     | 0.818 | 0.692 | 0.760 | 0.439    |
| human   | 0.779 | 0.604 | 0.672 | 0.313    |
| vehicle | 0.857 | 0.779 | 0.848 | 0.565    |

Train: imgsz 1280, batch 32, 100 epochs, ~2.0 h on RTX PRO 6000.  
Export ONNX: imgsz 640, opset 17.  
`detector_alpha.onnx` sha256: `40151159e7bf59fcfc24b591124ff7aeec88ff4365619ee701fc186efdce199a`

## Classes (head nc=13)

Trained with labels: **human (0), vehicle (1)**.  
Other CERBER ids (uav, landing_zone, … cargo) are in the head but **untrained** in v1.

## Files

- `best.pt` — Ultralytics weights  
- `best.onnx` / `detector_alpha.onnx` — flight ONNX (`yolo_v8_raw`)  
- `results.csv` / `results.png` — train curves  

## Cite

VisDrone: https://github.com/VisDrone/VisDrone-Dataset  
Ultralytics YOLO (AGPL-3.0)
