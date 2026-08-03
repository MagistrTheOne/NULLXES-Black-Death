# NULLXES CERBER RT (Robot Track)

**Status:** READY TO SIGN — tech plan / ТЗ  
**Date:** 2026-08-03  
**Parent:** [CERBER.md](./CERBER.md) · [CERBER_VISION_STACK.md](./CERBER_VISION_STACK.md)  
**Stack:** Python 3.11 (perception / guidance / FM) + C++17/20 (L0 stop / drivers) · ROS 2 · ONNX Runtime  
**Constraint:** civil only · onboard inference · no cloud LLM in runtime

---

## 0. One-liner

**CERBER RT** = robot perception lane of NULLXES CERBER:  
**QR → human → indoor objects → free-space / wall proximity → stop**, reusing CERBER Vision pipeline (preprocess → ONNX → NMS → WorldFact), **without** reordering aerial Detect class ids.

```
NULLXES CERBER
    ├── CERBER (aerial / Alpha)     detector_alpha(_v2).onnx   LOCKED ids
    └── CERBER RT (robot)           detector_rt_v1.onnx        separate ids + config
```

---

## 1. Goal (acceptance — what “done” means)

On the delivered robot, onboard, no cloud:

| # | Capability | Pass criterion |
|---|------------|----------------|
| R1 | **QR** | Decode ≥1 valid QR @ 1–3 m, ≥15 FPS pipeline, publish fact `kind=qr` + payload string |
| R2 | **Human** | Detect person box conf ≥0.35, stable ≥0.5 s track id (when Track online) |
| R3 | **Objects** | Detect ≥ {chair, table, door, obstacle} on robot camera domain; mAP50 ≥ **0.55** on held-out robot set (≥200 images) |
| R4 | **No wall hit** | Approach wall at crawl speed → **hard stop** before contact (margin ≥ **0.35 m** or bumper trigger); L0 stop independent of Python crash |
| R5 | **Fail-closed** | Missing/bad ONNX sha256 → no silent fake detections; FM → SAFE_STOP |

Mission demo loop (sign-off demo):

1. See QR → read payload → log + WorldFact  
2. See human → announce / publish  
3. See chair/table → publish boxes  
4. Drive toward wall / clutter → **stop** without collision  

---

## 2. Non-goals (explicit)

- Not replacing CERBER-CV aerial weights / class order  
- Not SLAM map as Flight-1 / RT v1 gate (optional later)  
- Not “wall as YOLO-only class” as sole safety  
- Not Ultralytics / torch in robot runtime  
- Not Alpha 5×5 geometry / aero scope  

---

## 3. Architecture (same papa stack)

```
 Cameras / depth / bumpers
           │
           ▼
 ┌─────────────────────────────────────────┐
 │  Python 3.11 — CERBER RT (L1–L5)        │
 │  vision preprocess                      │
 │  ├─ L1 Detect ONNX  (detector_rt_v1)    │
 │  ├─ QR Decoder      (OpenCV/zxing)      │  ← parallel, not YOLO
 │  ├─ L3 Track        (BoT-SORT)          │
 │  └─ Range / seg hint → proximity        │
 │           │                             │
 │           ▼                             │
 │  Fusion → WorldFact / SoftBus / ROS 2   │
 │  Guidance: crawl / avoid / stop request │
 │  FM: health, SAFE_STOP mode             │
 └──────────────────┬──────────────────────┘
                    │ stop / speed limit setpoint
                    ▼
 ┌─────────────────────────────────────────┐
 │  C++ L0 — robot safety loop             │
 │  velocity clamp · e-stop · bumper latch │
 │  setpoint stale → STOP                  │
 └─────────────────────────────────────────┘
```

| Layer | Owns | Language |
|-------|------|----------|
| QR decode | payload string, bbox/ROI optional | Python |
| Detect RT | boxes + class ids (robot schema) | Python + ORT |
| Track | temporal IDs | Python |
| Proximity | depth/LiDAR/ultrasonic → `d_min` | Python (+ C++ driver if bus) |
| Guidance | speed cmd / stop request | Python |
| **Hard stop** | bumper, stale cmd, e-stop | **C++ L0** |
| FM | SAFE_STOP / recover | Python |

**Rule:** Detect may *request* stop. **L0 + bumper + range gate** *enforce* stop.

---

## 4. Detect class schema — CERBER RT v1 (LOCKED for RT train)

**Separate yaml.** Do **not** reuse aerial id order for training RT.

| id | class | Priority |
|----|-------|----------|
| 0 | human | R2 |
| 1 | chair | R3 |
| 2 | table | R3 |
| 3 | door | R3 |
| 4 | obstacle | R3 / clutter |
| 5 | wall_segment | weak prior only — **not** sole safety |
| 6 | qr_panel | optional visual cue; decode is separate |
| 7 | robot | other platforms / self-view if needed |
| 8 | cargo_box | indoor logistics stretch |
| 9 | unknown_object | catch-all low priority |

Config / weights naming:

| Artifact | Path |
|----------|------|
| Train project | Ultralytics project `cerber-rt-detect` |
| Flight ONNX | `06_autonomy/models/onnx/detector_rt_v1.onnx` |
| Config + sha256 | `06_autonomy/models/configs/detector_rt_v1.yaml` |
| Metrics doc | `00_docs/architecture/CERBER_RT_METRICS_v1.md` (after first train) |

Aerial `detector_alpha*.yaml` remains untouched.

---

## 5. QR lane (mandatory, parallel)

| Item | Choice |
|------|--------|
| Library | OpenCV QRCodeDetector **or** zxing-cpp Python binding |
| Trigger | full frame @ detect FPS; optional ROI from `qr_panel` box |
| Output | `/bd/rt/qr` · WorldFact `kind=qr`, `payload`, `confidence`, stamp |
| Fail | no code → empty; never block Detect |

---

## 6. Anti-collision (R4) — layers

| Layer | Sensor | Action |
|-------|--------|--------|
| L0 bumper / contact | bumper / FSR | latch STOP until clear + reset |
| Range gate | depth cam **or** 2D LiDAR **or** ultrasonic front | if `d_min < D_STOP` → STOP |
| Soft slow | same | if `d_min < D_SLOW` → crawl vmax |
| CV assist | Detect `obstacle` / weak `wall_segment` | reduce speed; **cannot** be only barrier |

**Default trips (tunable after HW arrive, lock in safety md):**

| Param | Default |
|-------|---------|
| `D_STOP` | 0.35 m |
| `D_SLOW` | 0.80 m |
| `V_CRAWL` | ≤ 0.15 m/s during RT demo |
| Setpoint stale | 200 ms → L0 STOP (same philosophy as Alpha) |

---

## 7. Repo layout (add under existing CERBER tree)

```
06_autonomy/
  perception/
    vision/                 # shared preprocess / ORT session (extend, don't fork blindly)
    qr/                     # NEW — CERBER RT QR decoder + node
    tracking/               # BoT-SORT (shared aerial/RT)
    fusion/                 # RT proximity + fact merge
    sensors/                # robot cam / depth / lidar adapters
  models/
    onnx/detector_rt_v1.onnx
    configs/detector_rt_v1.yaml
    datasets/cerber_rt/     # robot domain set
    scripts/train_cerber_rt_detect.py
  ros2/nodes/
    vision_rt_soft.py
    qr_rt_soft.py
    proximity_rt_soft.py
  control/guidance/
    robot_crawl_guidance.py
05_avionics/                # or robot L0 package when HW known
  … L0 STOP / bumper driver (C++)
01_requirements/safety/
  CERBER_RT_FM_THRESHOLDS.md
00_docs/architecture/
  CERBER_RT.md              # this file
```

---

## 8. Hardware — robot ask (what we need when kit arrives)

Minimum to start “красоту”:

| Subsystem | Requirement | Why |
|-----------|-------------|-----|
| Compute | x86_64 or Jetson with CUDA **or** ORT-capable NPU; Linux preferred | ORT + ROS 2 |
| RGB cam | ≥1280×720 @ ≥20 FPS, known intrinsics later | Detect + QR |
| Depth **or** LiDAR **or** front ultrasonic | one ranging source mandatory for R4 | wall stop |
| Bumper / e-stop | at least front contact OR hardware e-stop | L0 latch |
| Base | differential / holonomic with velocity cmd interface | crawl demo |
| Power | stable 5 V/12 V for cams + compute | bench |

**Nice-to-have:** second RGB, IMU, wheel odometry, GPU on-robot (see §9).

On arrival — fill inventory sheet (serials, topic names, max speed, bumper polarity) before first train on robot domain.

---

## 9. GPU — what to request (sign this block)

### 9.1 Train / fine-tune (host or cloud — NOT robot)

| Tier | GPU | VRAM | Use |
|------|-----|------|-----|
| **Minimum** | RTX **4060 Ti 16 GB** / **4070 Ti** | 12–16 GB | yolov8s/n RT, imgsz 640, small batches |
| **Recommended** | RTX **4090 24 GB** / **L40S 48 GB** / **RTX PRO 6000** | 24–48 GB | yolov8s/m, imgsz 1280, batch 16–32, fast FT |
| **NULLXES parity** | same class as CERBER Stage 1 (**RTX PRO 6000** / A100 40) | 40–48 GB | one pipeline for aerial + RT |

Train stack (offline only): PyTorch + Ultralytics → export ONNX opset 17 → sha256 into yaml.

**Request line for procurement:**  
> 1× GPU node ≥24 GB VRAM (prefer 4090 / L40S / RTX PRO 6000), CUDA 12.x, for CERBER RT Detect train/export. Duration: 2–4 weeks burst + on-demand FT after robot cam domain collected.

### 9.2 Onboard robot inference

| Platform | OK for RT v1? | Notes |
|----------|---------------|-------|
| Laptop / NUC + **RTX 3050+** | yes | easiest bring-up |
| **Jetson Orin NX 8/16 GB** | yes | ORT CUDA / TensorRT later |
| Jetson Orin Nano | borderline | yolov8n, imgsz 640, FPS budget |
| CPU-only ORT | bring-up only | not R4 demo quality |

**Request line:**  
> Robot compute with CUDA ORT path (Orin NX class **or** companion PC with discrete GPU). Depth or LiDAR mandatory.

---

## 10. Data plan

| Source | Role |
|--------|------|
| COCO subset (person, chair, table) | cold start pretrain / remap |
| Open Images / Roboflow indoor (door, furniture) | fill classes |
| **Robot egocentric** (mandatory) | 500–2000 frames after HW: QR cards, humans, chairs, tables, walls at crawl |
| Hold-out | 20% robot frames locked for metrics |

Label format: YOLO txt · Ultralytics data yaml `cerber_rt_data.yaml`.  
QR: mostly decode lane; optional `qr_panel` boxes for ROI assist.

---

## 11. Phases (execute after signature + HW)

### Phase RT-0 — Sign-off & prep (no robot)

- [ ] Sign this doc + GPU request §9  
- [ ] Skeleton: `detector_rt_v1.yaml` (empty sha), `qr/` package, proximity stub  
- [ ] Cold-start train on public indoor remap → draft ONNX (bench FPS)  

**Gate:** draft ONNX runs in existing VisionPipeline path on host.

### Phase RT-1 — Robot power-on (HW arrived)

- [ ] Inventory sheet: cams, depth/LiDAR, bumper, max speed, OS, CUDA  
- [ ] Camera → preprocess → host/robot ORT smoke  
- [ ] QR decoder live smoke  
- [ ] Bumper + range → C++ L0 STOP smoke (even without Detect)  

**Gate:** R1 QR + R4 mechanical/range stop work **without** neural net.

### Phase RT-2 — Domain Detect

- [ ] Collect ≥500 labeled robot frames  
- [ ] FT `cerber-rt-detect` on §9 GPU  
- [ ] Export `detector_rt_v1.onnx` + sha256 fail-closed  
- [ ] Metrics doc · human/chair/table mAP  

**Gate:** R2 + R3 on robot cam.

### Phase RT-3 — Integrated demo

- [ ] Detect + QR + proximity → WorldFact  
- [ ] Crawl guidance + SAFE_STOP  
- [ ] Record demo log (QR payload, boxes, `d_min`, stop event)  
- [ ] Unit/contract tests: L0 does not import Detect; sha fail-closed  

**Gate:** full §1 table green → **CERBER RT v1 ACCEPTED**.

### Phase RT-4 — Adaptive (post-v1)

- [ ] Per-robot FT / calibration pack (intrinsics, `D_STOP`)  
- [ ] BoT-SORT IDs for human  
- [ ] Optional weak wall seg; still range-primary  
- [ ] TensorRT EP if Orin  

---

## 12. Interfaces (topics — draft, lock with HW)

| Topic | Content |
|-------|---------|
| `/bd/rt/detections` | RT Detect boxes |
| `/bd/rt/qr` | payload + pose hint |
| `/bd/rt/proximity` | `d_min`, source, stamp |
| `/bd/rt/health` | cams / ORT / range / bumper |
| `/bd/fm/mode` | includes `SAFE_STOP` |
| `/bd/l0/setpoint` | speed / stop — L0 consumes |
| `/bd/dmi/world_fact` | optional bridge for multi-agent later |

---

## 13. Safety / FM (robot)

| Mode | Enter | Action |
|------|-------|--------|
| NOMINAL_CRAWL | health OK, `d_min ≥ D_SLOW` | ≤ crawl vmax |
| SLOW | `D_STOP ≤ d_min < D_SLOW` | reduce speed |
| SAFE_STOP | `d_min < D_STOP` OR bumper OR ORT/cam fail critical | zero cmd; L0 latch |
| HOLD | operator / e-stop | no motion |

Civil indoor only. No weapons framing. Obstacle classes = collision / navigation awareness.

---

## 14. Deliverables checklist (for signature)

| Deliverable | Owner |
|-------------|-------|
| This plan accepted | NULLXES systems |
| GPU node ≥24 GB VRAM (§9.1) | partner / infra |
| Robot kit with RGB + range + bumper (§8) | partner |
| `detector_rt_v1` ONNX + metrics | autonomy |
| QR + proximity + L0 STOP integrated demo | autonomy + avionics |
| `CERBER_RT_FM_THRESHOLDS.md` locked post-HW | systems |

---

## 15. Success definition (contract language)

> CERBER RT v1 is accepted when the robot, onboard, using NULLXES Python+C++ stack and local ONNX, continuously detects humans and indoor objects, decodes QR payloads, and performs a commanded crawl toward an obstacle/wall culminating in a **non-contact stop** enforced by ranging and/or bumper with L0 independence from Python faults.

---

## Refs

- [CERBER.md](./CERBER.md)  
- [CERBER_STATUS.md](./CERBER_STATUS.md) (aerial Stage 2 parallel)  
- [AUTONOMY_ARCHITECTURE.md](./AUTONOMY_ARCHITECTURE.md)  
- [HOW_TO_WRITE.md](../conventions/HOW_TO_WRITE.md)  
- ADR-001 Alpha demonstrator (aerial) — RT does not reopen Alpha geometry  
