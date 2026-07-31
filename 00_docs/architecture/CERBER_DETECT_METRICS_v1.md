# CERBER Detect — Metrics v1

**Model:** [MagistrTheOne/CERBER-CV](https://huggingface.co/MagistrTheOne/CERBER-CV)  
**Run:** `cerber-detect/v1` · **Date:** 2026-07-31  
**Status doc:** [CERBER_STATUS.md](./CERBER_STATUS.md)

## Setup

| Item | Value |
|------|--------|
| Base | yolov8s.pt → nc=13 CERBER head |
| Train imgsz | 1280 |
| Batch | 32 |
| Epochs | 100 (~2.015 h) |
| GPU | NVIDIA RTX PRO 6000 Blackwell (~97 GB) |
| Data | VisDrone-DET remapped → `human`/`vehicle` only |
| Val set | 548 images · 38758 instances |
| Export | ONNX imgsz **640**, opset **17** |
| Params (fused) | ~11.13 M |

## Final validation (`best.pt`)

| Class | Images | Instances | P | R | mAP50 | mAP50-95 |
|-------|--------|-----------|---|---|-------|----------|
| **all** | 548 | 38758 | 0.818 | 0.692 | **0.760** | **0.439** |
| human | 531 | 13969 | 0.779 | 0.604 | 0.672 | 0.313 |
| vehicle | 546 | 24789 | 0.857 | 0.779 | 0.848 | 0.565 |

Speed (train GPU, imgsz 1280 val pass): ~1.1 ms inference / image (Ultralytics report).

## ONNX

| Field | Value |
|-------|--------|
| Layout | `yolo_v8_raw` |
| I/O | `images` → `output0` shape `(1, 17, 8400)` |
| Flight file | `06_autonomy/models/onnx/detector_alpha.onnx` |
| sha256 | `40151159e7bf59fcfc24b591124ff7aeec88ff4365619ee701fc186efdce199a` |

Smoke: same val frame — PT ~9 human / 39 vehicle; ONNX ~10 / 35 (letterbox 384×640 vs 640×640). Acceptable for v1.

## Notes

- Head has 13 CERBER classes; **only 0–1 trained**. Do not claim uav/landing/fire performance.
- Re-val: [Ultralytics Val](https://docs.ultralytics.com/modes/val) on `best.pt` / `best.onnx` + `cerber/data.yaml`.
- Stage 2 (from **2026-08-02**): onboard integration metrics = latency + qualitative boxes, not new mAP unless new labels.
