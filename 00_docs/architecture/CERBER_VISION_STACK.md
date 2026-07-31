# CERBER Vision Stack — Canon (LOCKED 2026-07-31)

Engineering roadmap (not a model shopping list). Aligns with GPT review + NULLXES repo layout.  
**Do not reorder Detect class ids** — flight ONNX v1/v2 already trained on `detector_alpha.yaml` order.

## Layers

```
Camera → Vision preprocess
              │
              ├─► L1 Detect     (boxes + class)
              ├─► L2 Segment    (surface / land-cover)     [separate service]
              └─► L3 Track      (IDs across frames; no new net)
                        │
                        ▼
                   L5 Fusion    (one scene state → DMI / guidance)
                        │
                        ▼
                   L4 Navigation decision  (where fly / no-fly / land)
```

| Layer | Job | Runtime now | Next |
|-------|-----|-------------|------|
| **L1 Detect** | What is in the frame? | `detector_alpha_v2.onnx` (YOLOv8) | YOLO26 only after layout/FPS/export gate |
| **L2 Segment** | What is the surface? | not shipped | SegFormer + LoveDA/LandCover |
| **L3 Track** | Same object N frames ago? | not shipped | BoT-SORT on Detect stream |
| **L4 Navigation** | Where fly / land / avoid? | not shipped | OpenLander trial → custom SLZ |
| **L5 Fusion** | One decision, not four opinions | partial EKF + DMI | fuse Detect+Seg+Track → WorldFact |

Navigation is **decision**, not another detector. Fusion is where “intelligence” appears.

## L1 Detect — class ids (LOCKED)

Exact order in `06_autonomy/models/configs/detector_alpha.yaml` / `_v2.yaml`:

| id | Class |
|----|--------|
| 0 | human |
| 1 | vehicle |
| 2 | uav |
| 3 | landing_zone |
| 4 | obstacle |
| 5 | power_line |
| 6 | road |
| 7 | building |
| 8 | forest |
| 9 | water |
| 10 | fire |
| 11 | infrastructure |
| 12 | cargo |

Trained today: **0,1** (v1) · **0,1,2** (v2). Rest = head slots only.

Conceptual GPT grouping (objects vs surfaces vs infra) is fine for docs; **ids stay as above**.

## L2 Segment — surfaces (separate service)

Not object search. Pixel / region labels, e.g.:

`road` · `grass` · `forest` · `building` · `water` · `field`

Base: SegFormer · LoveDA · LandCover.ai  
Repo target: `06_autonomy/perception/segmentation/` (sibling of `vision/`).

## L3 Track

No second inference net. Association after Detect.  
Default: **BoT-SORT**; ByteTrack if FPS-bound.  
Target: `06_autonomy/perception/tracking/`.

## L4 Navigation

Inputs: Detect + Segment + Track.  
Outputs: fly / no-fly / safe land / obstacle corridors.  
Start: OpenLander ONNX; replace with CERBER Nav later.  
Target: `06_autonomy/perception/navigation/`.

## L5 Fusion

Example:

- Segment → road  
- Detect → vehicle  
- Track → same vehicle, ~11 m/s  
- Nav → do not cross trajectory  

Autopilot gets **one** fused scene act, not four votes.  
Code: `perception/fusion/` (vision facts) + `06_autonomy/dmi/` (mission / world cache). Nav EKF stays GNSS+IMU; do not conflate with CV fusion.

## Repo layout (under existing tree — no parallel `cerber/` root)

```
06_autonomy/
  perception/
    vision/           # preprocess + Detect ONNX (exists)
    segmentation/     # SegFormer service (to add)
    tracking/         # BoT-SORT (to add)
    navigation/       # OpenLander / planner (to add)
    fusion/           # EKF + CV scene fusion (EKF exists)
  models/
    onnx/ configs/ weights/ datasets/ scripts/
  dmi/                # mission-level consumer of fused facts
```

Weights stay gitignored; configs + sha256 in git.

## YOLO26 gate (do not rush flight swap)

Before replacing CERBER-CV ONNX:

1. **ONNX layout** — must map to or ADR-replace `yolo_v8_raw` `[1, 4+nc, N]` (decoder / NMS / export).  
2. **FPS / memory** on target host — +2% mAP with −35% FPS = fail for flight.  
3. **Export matrix** — ORT · TensorRT · OpenVINO · Orange Pi / Jetson when those boards exist.

Until then: train experiments on YOLO26 offline; flight = v2 YOLOv8 ONNX.

## August 2026 plan (minimize blast radius)

1. Wire **BoT-SORT** to `detector_alpha_v2.onnx` stream.  
2. Detect++ FT: **FLAME** (fire) + **InsPLAD/MPID** (power_line) — new Hub revision, do not break v2 path.  
3. Stand up **SegFormer** service (LoveDA/LandCover).  
4. **Fusion engine** sketch: Detect+Seg+Track → DMI WorldFact.  
5. Only then A/B YOLO26 vs CERBER-CV-v2 on same data (mAP · latency · VRAM · ONNX compat).

## Refs

- [CERBER.md](./CERBER.md) · [CERBER_DATASETS.md](./CERBER_DATASETS.md) · [CERBER_MODEL_SOURCES_2026-07-31.md](./CERBER_MODEL_SOURCES_2026-07-31.md)  
- Metrics: v1 / v2 · Hub Collection nullxes-black-death-uav
