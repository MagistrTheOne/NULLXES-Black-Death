# REPO STATUS MAP — NULLXES BLACK DEATH

**Date:** 2026-08-08 · FS + code audit after SoftBus perception P0 land  
**Supersedes autonomy rows in** `IMPLEMENTATION_GAP_MAP.md` (2026-08-04) for perception/DMI/L0Bridge.  
**Legend:** `HAS_CODE` · `HAS_DATA` · `DOC_ONLY` · `MIXED` · `EMPTY` · `BLOCKED` · `PENDING` · `DEPRECATED`

Правило чтения: **папка с кодом ≠ flight-ready.** Смотри колонку Reality.

---

## Domain rollup

| Folder | Tag | Reality (one line) |
|--------|-----|--------------------|
| `00_docs` | DOC_ONLY | Canon. ADR-001/002/004/005 Accepted; ADR-003 Proposed. |
| `01_requirements` | DOC_ONLY | Alpha 5×5 locked requirements + FM thresholds. |
| `02_aerodynamics` | MIXED | Scripts + airfoil `.dat`; polars/CFD **BLOCKED** (no invented CL-CD). |
| `03_structure` | MIXED | Loadpath notes + thin spar CSV; FEA not CalculiX; `landing_gear/` empty. |
| `04_propulsion_energy` | DOC_ONLY | Battery/PDB/thermal notes chained to analytic aero. |
| `05_avionics` | MIXED | L0 C++ inner_loop lib real; `drivers/` empty; BOM not locked. |
| `06_autonomy` | MIXED | SoftBus Flight-1 chain HAS_CODE; packs/VIO native/calib flight **pending**. |
| `07_simulation` | MIXED | `cerber_studio` primary; lab DEPRECATED; Gazebo/AirSim/HIL twin BLOCKED. |
| `08_prototypes` | DOC_ONLY | Practice / bench / build-order plans. |
| `09_manufacturing` | DOC_ONLY | Layup + assembly notes; qa/tooling empty. |
| `10_tests` | MIXED | Unit HAS_CODE (~17); integ/HIL/flight BLOCKED/empty. |
| `99_tools` | MIXED | L0 smoke + CI yaml; **not** wired under `.github/workflows`. |
| `datasets/` | HAS_DATA (local) | **gitignored.** VisDrone only; CERBER/POSEIDON merged roots missing. |
| `runs/` | HAS_DATA (local) | **gitignored.** Only `v2-pursuit-2080` has weights. |

---

## `00_docs` — DOC_ONLY

| Path | Status | Note |
|------|--------|------|
| `adr/ADR-001…005` | Accepted except **ADR-003 Proposed** | RT unsigned |
| `architecture/ONBOARD_PERCEPTION_RESEARCH_2026-08.md` | Current | Plane Guided, P0/P1 |
| `architecture/DMI_ONTOLOGY.md` | Canon | WorldObject / Relations / Events |
| `architecture/TRACE_SPEC.md` | Canon | trace_id Flight Recorder |
| `architecture/MODEL_RELEASE_SPEC.md` | Canon | STABLE/CANDIDATE ModelPack |
| `architecture/MISSION_POLICY_SPEC.md` | Canon | Runtime MissionProfile gate |
| `architecture/SEGMENTATION_LANES.md` | Canon | SceneSeg / VehicleAttr / ObsInterest |
| `architecture/FLIGHT1_BOM_LOCK.md` | PENDING | All HW rows open |
| `architecture/IMPLEMENTATION_GAP_MAP.md` | **STALE** (2026-08-04) | Use this file for autonomy |
| `architecture/CERBER_STATUS.md` | Partial | Stage1 done / Stage2 open |
| `ALPHA_LESSONS_LEARNED.md` | BLOCKED empty | After Flight-1 |
| `Павлыш_с11_16.pdf` | Reference PDF | Not architecture canon |

**Confusion:** `SYSTEM_OVERVIEW` / product 50×50 vs Alpha 5×5 demonstrator (ADR-001).

---

## `01_requirements` — DOC_ONLY

| Path | Status |
|------|--------|
| `ALPHA_5x5_REQUIREMENTS.md` | Locked baseline |
| `missions/MISSIONS.md` | Civil classes (product envelope) |
| `interfaces/ALPHA_5x5_ROS_TOPICS.md` | Topic contract (SoftBus ahead of bd_interfaces) |
| `safety/*_FM_THRESHOLDS.md` | Real thresholds |

---

## `02_aerodynamics` — MIXED / BLOCKED leaves

| Path | Tag | Reality |
|------|-----|---------|
| `airfoils/*.dat` | HAS_DATA | Real Selig coords |
| `airfoils/polars/` | BLOCKED | Intentional empty |
| `airfoils/sections_blended/` | BLOCKED | Until blend validates |
| `geometry/` | MIXED | Generator + CSV; PLANFORM draft |
| `loads/ALPHA_5x5_PRELIM_AERO.md` | DOC_ONLY | **Analytic estimate — not XFOIL** |
| `scripts/run_xfoil_polars.py` | HAS_CODE | Exits BLOCKED without XFOIL |
| `cfd/` | EMPTY | |

**Confusion:** prelim aero ≠ validated polars. Do not size battery from it as flight truth.

---

## `03_structure` — MIXED

| Path | Tag | Reality |
|------|-----|---------|
| `ALPHA_5x5_LOADPATH.md`, `*_MASS_BREAKDOWN.md` | DOC_ONLY | Concept v0 |
| `load_paths/` + `scripts/export_spar_stations.py` | MIXED | Thin geometry export |
| `fea/` | DOC_ONLY | Hand/beam — not FEA results |
| `landing_gear/`, `mass/` | EMPTY | Mass doc is at folder root |

---

## `04_propulsion_energy` — DOC_ONLY

| Path | Tag |
|------|-----|
| `ALPHA_5x5_PROPULSION.md`, `energy_storage/`, `power_distribution/`, `thermal/` | DOC_ONLY |
| `propulsion/`, `scripts/` | EMPTY |

Numbers chained to analytic aero. PE-05 6 h rejected for Alpha.

---

## `05_avionics` — MIXED

| Path | Tag | Reality |
|------|-----|---------|
| `flight_software/inner_loop.*` | HAS_CODE | Algorithm lib only — no PWM/CAN/FC flash |
| `buses/`, `hardware/`, `timing/` | DOC_ONLY | Specs; HW not locked |
| `drivers/` | EMPTY | |

**Flight-1 path:** ArduPilot Plane on Matek H743 + `06_autonomy/l0_bridge` — not bare C++ L0 PWM.

---

## `06_autonomy` — MIXED (main stack)

### HAS_CODE (use this)

| Module | Path | Reality |
|--------|------|---------|
| SoftBus | `soft_bus/` | Primary flight message layer |
| SensorHub | `perception/sensors/` | OpenCV cam + FC telemetry → SoftBus |
| Calib | `perception/calibration/` + `calib/*.yaml` | Loader real; YAML = **bench placeholder** |
| CERBER Detect | `perception/vision/` + `models/onnx/detector_alpha*.onnx` | Pipeline real; needs live cam |
| Track | `perception/tracking/` BoT-SORT + IOU fallback | Real |
| Fusion | `perception/fusion/` scene + EKF + nav_fuse | WorldFact ENU+cov |
| SceneAnalyst | `fusion/scene_analyst.py` | Rules, no LLM |
| POSEIDON runtime | `poseidon/` | Fail-closed router |
| DMI | `dmi/` | WorldCache / offer / claim / intent→goal |
| Guidance | `control/guidance/` | simple + track civil modes |
| FM / AlphaBT | `fault_management/`, `planning/behaviour/` | Real soft logic |
| Dual-compute | `core/dual_compute/` | SoftBus HB/election |
| ArduPlane adapter | `l0_bridge/` | Plane Guided (not Copter) |
| Soft nodes | `ros2/nodes/*_soft.py` | SoftBus wrappers |
| Bench tools | `tools/flight1_bench_chain.py` | Software birth chain |

### Present but NOT flight-loaded

| Module | Tag | Reality |
|--------|-----|---------|
| POSEIDON packs | EMPTY weights | Manifests only; `sha256: pending`; no `model.onnx` |
| SegFormer service | HAS_CODE shell | No ONNX → `ok=false` |
| Depth service | HAS_CODE shell | Empty grid until FLIGHT-2 |
| IVioProvider | Contract | OpenVINS/Basalt → `degraded` until native lib |
| `calib/*.yaml` | Bench | Not Kalibr flight truth |
| Py L0 `l0_soft` | Soft twin of C++ | Not FC replacement |

### BLOCKED / EMPTY

| Path | Tag |
|------|-----|
| `planning/trajectory/`, `planning/missions/` | BLOCKED |
| `core/state|decision|health|interfaces` | BLOCKED / EMPTY (Alpha: FM+BT enough) |
| `control/actuators/`, `control/inner_loop/` dirs | EMPTY (impl elsewhere) |
| `perception/qr/`, `perception/navigation/` | absent |
| `models/torchscript/` | EMPTY |
| `ros2/bd_interfaces/` | **STALE** vs SoftBus topics |

### Product trinity (canon)

```
CERBER   = SENSE   (general detect)
POSEIDON = SPECIALIZE (local ONNX packs — runtime in image, weights via registry)
DMI      = DECIDE  (mission / swarm)
```

---

## `07_simulation` — MIXED

| Path | Tag | Reality |
|------|-----|---------|
| `cerber_studio/` | HAS_CODE | Primary IDE |
| `cerber_lab/` | DEPRECATED | Do not use |
| `gazebo/`, `airsim/`, `soft_runtime/` | BLOCKED | Proxy / wrong vehicle / no fakes |
| `hil/`, `scenarios/` | HAS_DATA templates | Not automated HIL |
| `digital_twin/` | topic_map only | |

---

## `08_prototypes` — DOC_ONLY

Practice airframe TEST_PLANs, avionics bench intent, scale build order. `subsystem_rigs/` EMPTY.

---

## `09_manufacturing` — DOC_ONLY

Layup + assembly notes. `qa/`, `tooling/` EMPTY. After Flight-1.

---

## `10_tests` — MIXED

| Path | Tag |
|------|-----|
| `unit/` (~17 tests) | HAS_CODE — SoftBus/DMI/fusion/track/bench |
| `practice/bench_smoke_contracts.py` | HAS_CODE static |
| `integration/` | BLOCKED (README; orphan `__pycache__`) |
| `hil/` | DOC plan only |
| `flight/`, `regression/` | EMPTY |

---

## `99_tools` — MIXED

| Path | Tag | Reality |
|------|-----|---------|
| `host/l0_smoke_main.cpp` | HAS_CODE | Synthetic InnerLoop link |
| `ci/github_actions_smoke.yml` | DOC stub | **Not** under `.github/workflows` |
| `lint/`, `scripts/` | EMPTY | |

---

## `datasets/` + `runs/` — local HAS_DATA, gitignored

| Path | Reality |
|------|---------|
| `datasets/VisDrone/` | Present locally (~3.6 GB) |
| `datasets/cerber*`, `poseidon*` | **Missing** vs train yamls |
| `runs/detect/.../v2-pursuit-2080` | Has `best.pt` / onnx |
| Other run packs | Plots only / names outdated in docs |

Tracked configs live in `06_autonomy/models/datasets/` (yaml/docs only).

---

## Do not confuse

1. **SoftBus ahead of `bd_interfaces`** — SoftBus is SoT for Flight-1 topics.  
2. **Two L0 stories** — C++ lib (`05`) vs ArduPlane bridge (`06/l0_bridge`). Flight-1 = Plane+H743.  
3. **POSEIDON folder ≠ packs loaded** — runtime yes, ONNX no.  
4. **Calib YAML in repo ≠ flight calibration.**  
5. **Prelim aero ≠ XFOIL/CFD.**  
6. **cerber_lab DEPRECATED** — use `cerber_studio`.  
7. **Gap map 2026-08-04** — tracking/sensors/fusion rows obsolete; use this map.  
8. **`perception/README.md`** — updated 2026-08-08 to match code.  
9. **CI yaml in `99_tools` does not run on GitHub** until moved to `.github/workflows`.  
10. **Weapons / cloud LLM in flight path** — never (ADR-004/005).

---

## Next gates (honest)

| Gate | Blocker |
|------|---------|
| Freeze FLIGHT-1 HW | Fill `FLIGHT1_BOM_LOCK.md` |
| Physical birth E2E | Cam + H743 + Orin props-off |
| POSEIDON specialists | Export `uav_seraphim/model.onnx` + sha |
| VIO ok status | Native OpenVINS/Basalt + license |
| Validated aero/energy | XFOIL polars → re-size battery |
| CI on PR | Wire `.github/workflows` from `99_tools/ci` |
