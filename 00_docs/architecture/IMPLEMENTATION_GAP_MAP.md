# Implementation Gap Map — NULLXES BLACK DEATH

**Date:** 2026-08-04 · FS audit · no runtime  
**Legend:** DOC_ONLY · SKELETON · PARTIAL · HAS_CODE

---

## Domain rollup

| Domain | Code | Note |
|--------|------|------|
| `00_docs` / `01_requirements` | DOC_ONLY | Canon — not “implement as code” |
| `02_aerodynamics` | PARTIAL | scripts+dat; polars/CFD BLOCKED |
| `03_structure` | PARTIAL | notes + thin export |
| `04_propulsion_energy` | DOC_ONLY | Alpha energy notes |
| `05_avionics` | PARTIAL | L0 C++; drivers empty |
| `06_autonomy` | HAS_CODE core | Detect/DMI/dual/SoftBus; Track/Seg/Nav missing |
| `07_simulation` | PARTIAL | **cerber_studio** primary; lab deprecated; twin BLOCKED |
| `08` / `09` | DOC_ONLY | practice plans / mfg notes |
| `10_tests` | PARTIAL | unit OK; integ/HIL/flight BLOCKED |
| `99_tools` | PARTIAL | L0 smoke + CI yml |

---

## P0 queue (do these)

| # | Module | Now | Block | Implement next |
|---|--------|-----|-------|----------------|
| 1 | `perception/tracking/` | **absent** | not shipped | BoT-SORT → track_id on SoftBus |
| 2 | Stage 2 live cam | vision HAS_CODE | no HW driver | Webcam/host → ORT → `/bd/vision` |
| 3 | Detect → DMI | DMI HAS_CODE | no live bridge | WorldFact `kind=uav` |
| 4 | `perception/sensors/` | gitkeep | no drivers | cam / IMU adapters |
| 5 | `05_avionics/drivers/` | gitkeep | HW | IMU/FC → L0 |
| 6 | L0 bench hold | PARTIAL C++ | no real IMU | props-off hold |
| 7 | `cerber_v2` → v2b ONNX | pack HAS_CODE | RunPod not run | `detector_alpha_v2b.onnx` + sha |
| 8 | `control/guidance` chase | simple_guidance | no tracks | chase from track_id |
| 9 | Practice airframes | DOC plans | kit | edu power-on + IMU topic |
| 10 | `cerber_studio` | HAS_CODE | ORT/sha optional | run Studio + worker overlay |

**Artifacts:** v1/v2 ONNX **present** · v2b / RT ONNX **absent**.

---

## By subsystem — doc vs code

### CERBER / perception

| Path | Promise | Evidence | Next | P |
|------|---------|----------|------|---|
| `perception/vision/` | Detect ORT | HAS_CODE | live Stage 2 | P0 |
| `perception/tracking/` | BoT-SORT | **no dir** | create + unit | P0 |
| `perception/segmentation/` | SegFormer | **no dir** | August later | P2 |
| `perception/navigation/` | OpenLander | **no dir** | after Track | P2 |
| `perception/slam/` | OpenVINS | DOC BLOCKED Flight-1 | leave | lock |
| `perception/sensors/` | adapters | SKELETON | cam/IMU | P0 |
| `perception/fusion/` | EKF + CV fusion | PARTIAL EKF | CV fusion after Track | P1 |
| `perception/qr/` | CERBER RT | **absent** | after ADR-003 sign | P1 |
| `models/cerber_v2/` | v2b train pack | HAS_CODE | RunPod export | P0 |
| `detector_rt_v1` | RT Detect | yaml stub, no ONNX | cold-start after HW | P1 |

### Autonomy brain

| Path | Evidence | Next | P |
|------|----------|------|---|
| `dmi/` | HAS_CODE | bench coordinator↔agent | P0 |
| `dual_compute/` | HAS_CODE | 2-process failover real I/O | P0 |
| `fault_management/` | HAS_CODE | wire real health | P1 |
| `planning/behaviour/` | HAS_CODE AlphaBT | HW modes | P1 |
| `planning/trajectory/` | DOC_ONLY | min corridor | P1 |
| `planning/missions/` | DOC_ONLY | post-bench | P2 |
| `core/state|decision|health` | SKELETON / BLOCKED | Alpha: FM+BT enough | lock/P2 |
| `ros2/nodes` | HAS_CODE soft | live with drivers | P0 |
| `soft_bus/` | HAS_CODE | OK | — |

### Avionics / sim / proto / tests

| Path | Evidence | Next | P |
|------|----------|------|---|
| `05_avionics/flight_software` | PARTIAL | bench IMU | P0 |
| `05_avionics/drivers` | SKELETON | HAL | P0 |
| `07_simulation/cerber_studio` | HAS_CODE | Studio IDE | P0 |
| `07_simulation/cerber_lab` | DEPRECATED | use Studio | — |
| `gazebo` / `airsim` | SKELETON BLOCKED twin | real model later | P2 |
| `soft_runtime` | BLOCKED by policy | no fake runners | lock |
| `08_prototypes/practice_*` | DOC | execute TEST_PLAN_EDU | P0 |
| `09_manufacturing` | DOC | after Flight-1 | P2 |
| `10_tests/unit` | HAS_CODE | +track tests | P0 |
| `10_tests/integration|hil|flight` | BLOCKED | after drivers | P1 |

### Airframe disciplines

| Path | Evidence | P |
|------|----------|---|
| `02` polars / CFD | BLOCKED / empty | P1–P2 support |
| `03` FEA / landing_gear | DOC / empty | P2 |
| `04` propulsion code | DOC_ONLY | P2 |

---

## Intentional locks — do not “close with code” now

1. ADR-001 Alpha geometry / MTOW / 16 kg pack / stack — until Flight-1 + lessons  
2. Aerial Detect class id order — LOCKED  
3. `core/decision` separate arbitrator — FM+BT covers Alpha  
4. SLAM on Alpha Flight-1 — BLOCKED  
5. Soft twin / sensor mocks — PRODUCTION_FIRST forbidden  
6. 6 h / 300 km — out of Alpha  
7. CERBER RT full runtime — wait signature + robot HW  
8. YOLO26 flight swap — offline gate only  
9. Weapons / fire-control — never  
10. Seg L2 / Nav L4 — not Stage-2 blockers  

---

## Suggested next sprint order

```
edu kit IMU + L0 hold
    → live CERBER cam → DMI WorldFact
    → tracking/ BoT-SORT
    → RunPod cerber_v2 → v2b ONNX
    → guidance chase + cerber_studio
    → dual failover 2-process
```
