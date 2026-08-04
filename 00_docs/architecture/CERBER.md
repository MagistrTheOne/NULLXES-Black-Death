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

\*Segmentation — separate service (`perception/segmentation/`); Alpha may ship detect-only.

## Vision stack (LOCKED)

Full layer map · August plan · YOLO26 gate: **[CERBER_VISION_STACK.md](./CERBER_VISION_STACK.md)**

```
Detect → Track ─┐
Segment ────────┼─► Fusion → DMI / guidance
                │
         Navigation (decision)
```

Detect class ids: **do not reorder** — see `detector_alpha.yaml` (0 human … 12 cargo).

## Subsystems

| CERBER lane | Repo | Alpha status |
|-------------|------|--------------|
| Vision (ingest / preprocess) | `06_autonomy/perception/vision/` | letterbox + NCHW |
| Detection (L1) | vision + `models/onnx/` | CERBER-CV v1/v2 ONNX **shipped** |
| Tracking (L3) | `perception/tracking/` | TODO BoT-SORT |
| Segmentation (L2) | `perception/segmentation/` | TODO SegFormer |
| Navigation (L4) | `perception/navigation/` | TODO OpenLander → custom |
| Multi-Sensor / CV Fusion (L5) | `perception/fusion/` + `dmi/` | EKF partial; CV fusion TODO |
| Obstacle / scene recognition | detect + fused facts → DMI | WorldFact bridge |

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
| [CERBER_VISION_STACK.md](./CERBER_VISION_STACK.md) | **Canon layers** · August roadmap · YOLO26 gate |
| [CERBER_STATUS.md](./CERBER_STATUS.md) | Checklists · Stage 1 done · **Stage 2 from 2026-08-02** |
| [CERBER_DETECT_METRICS_v1.md](./CERBER_DETECT_METRICS_v1.md) | VisDrone scene · Hub CERBER-CV |
| [CERBER_DETECT_METRICS_v2.md](./CERBER_DETECT_METRICS_v2.md) | +UAV FT · Hub CERBER-CV-v2 |
| [CERBER_DATASETS.md](./CERBER_DATASETS.md) | VisDrone + Seraphim + planned |
| Hub v1 | [MagistrTheOne/CERBER-CV](https://huggingface.co/MagistrTheOne/CERBER-CV) |
| Hub v2 | [MagistrTheOne/CERBER-CV-v2](https://huggingface.co/MagistrTheOne/CERBER-CV-v2) |
| Collection | [nullxes-black-death-uav](https://huggingface.co/collections/MagistrTheOne/nullxes-black-death-uav-6a6c066b4f2f23d31e2a7d56) |
| Model sources (2026-07-31) | [CERBER_MODEL_SOURCES_2026-07-31.md](./CERBER_MODEL_SOURCES_2026-07-31.md) |

## CERBER V2 RunPod pack

Bare-metal train pack (no Docker): **`06_autonomy/models/cerber_v2/`**  
Prepare VisDrone + Seraphim + HF UAV extras → train `v2-pursuit` → `detector_alpha_v2b.onnx`.  
Cheat sheet: `06_autonomy/models/cerber_v2/README.md` · `scripts/runpod_all.sh`

## CERBER RT (Robot Track)

Ground robot lane — keep aerial ids locked; separate ONNX/schema.

| Doc | Content |
|-----|---------|
| [CERBER_RT.md](./CERBER_RT.md) | **ТЗ / plan** · acceptance · GPU · HW · phases |
| [ADR-003](../adr/ADR-003_CERBER_RT.md) | Decision lock · signature block |
| Config | `06_autonomy/models/configs/detector_rt_v1.yaml` |

Mission: QR → human → indoor objects → range/bumper stop (L0).  
Stack: same Python 3.11 + C++ L0 + ORT.

## Product mode — defensive pursuit (no weapons)

CERBER на BLACK DEATH / practice wing = **оборонный перехватчик-преследователь**:  
Detect → Track → pursue / escort / deny airspace presence.  
**Стек без вооружения.** Нет fire-control, боезарядов, targeting munitions.

| Lane | Job |
|------|-----|
| Detect `uav=2` | чужой БПЛА в FOV |
| Track (BoT-SORT) | держать ID при манёвре |
| Guidance | chase / intercept geometry (civil kinetic = body presence only) |
| DMI WorldFact | `kind=uav` для роя / координатора |

## Civil constraint

Obstacle / UAV = airspace awareness + defensive pursuit without weapons.  
CERBER RT: indoor navigation / logistics awareness only.  
No weapons / munitions datasets or framing in train or runtime.

## Refs

- Datasets / A100: `06_autonomy/models/datasets/DATASET_STACK_A100.md`  
- Brain map: `BRAIN_SCHEME.md`  
- Code root: `06_autonomy/perception/`
