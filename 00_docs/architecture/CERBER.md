# NULLXES CERBER

**Status:** LOCKED naming — perception system for BLACK DEATH / Black Judgment  
**Not:** «a detector» · «a neural net»  
**Is:** onboard **computer-vision / perception stack**

```
BLACK DEATH / Black Judgment
            │
            ▼
     NULLXES CERBER          ← perception system
            │
   ┌────────┼────────┬─────────┬──────────┐
   ▼        ▼        ▼         ▼          ▼
 Vision  Detection Tracking  Classify   Segment*
   │        │
   ▼        ▼
 YOLO (Ultralytics train → ONNX Runtime flight)
 OpenCV preprocess
        │
        ▼
 Multi-Sensor Fusion (GNSS+IMU EKF; LiDAR later)
        │
        ▼
 Obstacle / scene recognition → DMI world facts / FM / guidance
```

\*Segmentation — capability lane; Alpha Flight-1 may ship detect-only.

## Subsystems

| CERBER lane | Repo | Alpha status |
|-------------|------|--------------|
| Vision (ingest / preprocess) | `06_autonomy/perception/vision/` | letterbox + NCHW |
| Detection | same + `models/onnx/` | YOLO → ONNX; **BLOCKED** without weights |
| Tracking | perception (future module) | not shipped |
| Classification | via detect classes / later head | detect classes first |
| Segmentation | future | not Alpha-critical |
| Multi-Sensor Fusion | `perception/fusion/` | Nav EKF |
| Obstacle / scene recognition | detect + facts → DMI cache | DMI WorldFact bridge |

## Runtime stack (flight)

| Piece | Role |
|-------|------|
| Ultralytics YOLO | **offline train/export only** |
| ONNX Runtime | onboard inference |
| OpenCV | cameras / letterbox |
| Tracker | associate boxes across frames (when added) |
| Sensor fusion | EKF / later LiDAR association |

## Weights naming

| Name | Meaning |
|------|---------|
| **NULLXES CERBER** | whole perception product |
| Detect weights / runs | `cerber-detect` (Ultralytics project); ONNX `detector_alpha.onnx` until ADR renames |
| Draft name BLACKIRIS | superseded — do not use in new docs |

## Status / metrics / data

| Doc | Content |
|-----|---------|
| [CERBER_STATUS.md](./CERBER_STATUS.md) | Checklists · Stage 1 done · **Stage 2 from 2026-08-02** |
| [CERBER_DETECT_METRICS_v1.md](./CERBER_DETECT_METRICS_v1.md) | Val table · ONNX sha256 · Hub link |
| [CERBER_DATASETS.md](./CERBER_DATASETS.md) | VisDrone + planned stacks |
| Hub | [MagistrTheOne/CERBER-CV](https://huggingface.co/MagistrTheOne/CERBER-CV) |

## Civil constraint

Obstacle / UAV class = traffic & safety awareness. No combat / weapons framing.

## Refs

- Datasets / A100: `06_autonomy/models/datasets/DATASET_STACK_A100.md`  
- Brain map: `BRAIN_SCHEME.md`  
- Code root: `06_autonomy/perception/`
