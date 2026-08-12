# NULLXES BLACK DEATH — Onboard Perception / Navigation Research

**Date:** 2026-08-08  
**Scope:** Civil autonomy only (inspection, mapping, infrastructure, disaster, safe nav).  
**Analytical AI path:** POSEIDON — local specialist ONNX packs + SoftBus router (not conversational agents).  
**Out of scope:** weapons, fire-control, strike logic.  
**Production bus:** SoftBus (ROS2 = optional reference only).

Evidence tags: **FACT** · **MEASURED/BENCHMARK** · **INFERENCE** · **RECOMMENDATION** · **UNKNOWN / NEEDS TEST**

---

## A. Current architecture assessment

**FACT (repo):** Host/sim stack exists: CERBER YOLOv8 ONNX (`yolo_v8_raw`) → POSEIDON router/packs → IOU Track v1 → scene_fusion (pixel→ENU stub) → SceneAnalyst → WorldFact/DMI → guidance (incl. chase/escort/deny presence) → SoftBus. L0 C++ swarm-blind. Dual-compute / FM / LOITER-RTB logic present in software.

**FACT (gap):** `perception/sensors/` and `slam/` BLOCKED (README only). No production cam/IMU/GNSS adapters. No BoT-SORT. No SegFormer service. Pixel→ENU lacks calibrated extrinsics. POSEIDON pack ONNX weights pending export. HIL / real FC bridge incomplete.

**INFERENCE:** Current system is a **correct software skeleton** for onboard autonomy, not yet an onboard perception system — missing physical timing, drivers, and calibrated geometry.

---

## B. Missing capability map

| Capability | Status | Blocker |
|------------|--------|---------|
| Camera → `/bd/cam/*` | missing | drivers + carrier CSI/GMSL |
| IMU/GNSS → SoftBus | missing / FC-only | companion adapters + time sync |
| Calibrated projection | stub | Kalibr + mount CAD |
| Persistent MOT | IOU only | BoT-SORT + CMC |
| VIO | blocked | stereo/mono+IMU HW + license choice |
| Segmentation | absent | model + TRT budget |
| Depth / obstacle | absent | sensor choice |
| Dual-compute failover live | partial | real I/O + health |
| Thermal / FPS budget | unmeasured | onboard profiling |

---

## C. Recommended hardware architecture

### Companion compute — FACT (NVIDIA)

| Module | AI (sparse INT8) | GPU | CPU | Memory | Power modes | CSI |
|--------|------------------|-----|-----|--------|-------------|-----|
| **Orin NX 16GB** | up to **157 TOPS** | 1024-core Ampere, 32 TC | 8× A78AE | 16GB LPDDR5, 102.4 GB/s | 10 / 15 / 25 / **40W** + MAXN_SUPER (JetPack 6.2) | up to 4 cams (8 VC), 8 lanes |
| Orin NX 8GB | up to 117 TOPS | same GPU class | 6–8× A78AE (mode-dep.) | 8GB | 10 / 15 / 20 / 40W + MAXN_SUPER | same family |
| AGX Orin 32/64GB | up to 241–275 TOPS | 1792–2048 cores | 8–12× | 32–64GB | 15–60W (ind. higher) | up to 6 cams / 16 lanes |

Sources: [NVIDIA Jetson Orin product page](https://www.nvidia.com/en-us/autonomous-machines/embedded-systems/jetson-orin/); [JetPack 6.2 Super Mode blog](https://developer.nvidia.com/blog/nvidia-jetpack-6-2-brings-super-mode-to-nvidia-jetson-orin-nano-and-jetson-orin-nx-modules/); [Orin power/performance guide](https://docs.nvidia.com/jetson/archives/r35.6.1/DeveloperGuide/SD/PlatformPowerAndPerformance/JetsonOrinNanoSeriesJetsonOrinNxSeriesAndJetsonAgxOrinSeries.html).

**CONFLICT:** Some retail listings still quote Orin NX as “100 TOPS / 10–25W”. Treat **NVIDIA.com + JetPack 6.2 docs** as authoritative for Super/40W; verify flashed `nvpmodel` on the actual module.

**DLA:** Orin NX has **1× NVDLA v2**; AGX has **2×**. Useful for offloading a second network (e.g. SegFormer-B0 or specialist) while GPU runs CERBER — **NEEDS TEST** (ORT/TRT EP + layer support).

**RECOMMENDATION — FLIGHT-1 companion:** **Jetson Orin NX 16GB** on a drone-oriented carrier (CSI or GMSL deserializer, NVMe, UART to FC, active cooling).  
**RECOMMENDATION — FLIGHT-2 / heavy perception:** **AGX Orin 32GB** if concurrent Detect + specialist + Seg + VIO required at high rate.  
**BENCH:** Orin NX DevKit / carrier **or** x86+RTX (current 2080/6000 farm) for software; validate TRT engines on target SoM before flight.

### Concurrent workload suitability (INFERENCE + methodology)

Do **not** invent FPS. Methodology (**NEEDS TEST** on locked JetPack + `nvpmodel` + cooler):

1. Fix power mode (`nvpmodel -m …` + `jetson_clocks`).  
2. Measure alone: CERBER TRT FP16 imgsz 640; then +POSEIDON pack; then +BoT-SORT; then +VIO; then +Seg B0.  
3. Log: `tegrastats`, FPS, p50/p95 latency, dropped frames, Tj, power.  
4. Acceptance = sustained 30 min without thermal throttle below target FPS.

**MEASURED/BENCHMARK (external, not NULLXES stack):** Peer-reviewed Orin NX 16GB YOLOv8 TensorRT study (MAXN ~25W era, JetPack 5.1.1): TRT engines **~52–63% faster** than PyTorch; TRT high batch can OOM — cap batch for TRT ([Computers 2026, 15, 74](https://doi.org/10.3390/computers15020074)). Use as **methodology reference**, not as CERBER FPS claim.

---

## D. Sensor architecture

### Camera interface comparison

| Interface | Latency / cabling | Jetson fit | Airborne note |
|-----------|-------------------|------------|---------------|
| **MIPI CSI-2** | Lowest latency, short FFC | Native on Orin carriers | Best for rigid short mount |
| **GMSL2** | SerDes, FAKRA, up to ~15 m (vendor) | Needs deserializer (e-con, TechNexion, Basler, Imaging Source kits) | Best if cam far from companion / EMI |
| **USB3** | Higher & less deterministic latency | Easy bench | OK BENCH; weak for VIO timestamps |

**Global shutter:** Required for airborne CV / VIO (rolling shutter + vibration = bad). Examples: Sony Pregius **IMX568** 5MP GS GMSL2 for AGX Orin ([e-con NileCAM56](https://www.e-consystems.com/nvidia-cameras/jetson-agx-orin-cameras/imx568-5mp-gmsl2-global-shutter-camera.asp)); TechNexion GMSL GS family + Orin NX deserializer ([TechNexion GMSL flyer](https://www.technexion.com/wp-content/uploads/2025/10/GMSL2_camera_flyer_digitalview_042826.pdf), [VL-GM2-8CAM-RPI22](https://www.technexion.com/products/serdes/gmsl/gmsl2-frame-grabber/vl-gm2-8cam-rpi22/)); Imaging Source Orin reference designs ([TIS Jetson Orin](https://www.theimagingsource.com/en-us/embedded/kit/jetson-orin/)).

**RECOMMENDATION — FLIGHT-1 prototype:**  
1× **global-shutter** cam, **CSI** if mount ≤~20 cm from carrier; else **GMSL2** + Orin NX deserializer. Target **1080p@30–60** or **5MP@≥30** with M12 lens; FOV ~70–90° H for forward detect (exact FOV = NEEDS airframe). Skip USB for flight VIO.

### Calibration pipeline (FACT + RECOMMENDATION)

1. **Intrinsics + distortion** — chessboard/AprilGrid, Kalibr multi-cam or OpenCV.  
2. **Camera↔IMU extrinsics + time offset** — [Kalibr cam-IMU](https://github.com/ethz-asl/kalibr/wiki/Camera-IMU-calibration) (batch spline; needs clean header timestamps).  
3. **Camera↔body** — CAD mount + hand-eye / static transform YAML.  
4. **IMU intrinsics** — manufacturer / Allan variance before Kalibr.  
5. **GNSS antenna lever arm** — tape measure + CAD → NavEKF.

Store as SoftBus-loadable `calib/camera_forward.yaml` + `calib/imu0.yaml` + `T_body_cam`, `T_body_imu`, `td_cam_imu`.

---

## E. Perception architecture (process split)

Keep SoftBus; one responsibility per process/service:

| Service | In | Out | Rate target | Frame | Degraded |
|---------|----|-----|-------------|-------|----------|
| SensorHub | HW drivers | `/bd/cam/*`, imu, gnss | cam 30; imu 200–400; gnss 5–10 | sensor time | drop/stale flags |
| VisionService (CERBER) | cam | `/bd/vision/detections` | ≤ cam | image | last health fail |
| SpecialistRuntime (POSEIDON) | cam + hints | `/bd/poseidon/*` | budgeted | image | skip packs |
| Tracker | dets + (opt img for CMC) | `/bd/vision/tracks` | = detect | image | IOU fallback |
| VIO | cam + IMU | `/bd/nav/vio` | 20–50 | body | hold last / GNSS-only |
| Segmentation | cam | `/bd/vision/seg` | 5–15 | image | disable |
| SceneFusion | tracks+nav+calib | `/bd/dmi/world_fact` | ≤ track | **ENU** | low conf / image-only |
| SceneAnalyst | facts | `/bd/vision/scene` | ≤ fusion | ENU | LOITER suggest |
| DMI | facts/offers | intent/claim | event | mission | last intent |
| Guidance | goal/track+nav | `/bd/l0/setpoint` | 50 | body/ENU | SAFE_LOITER |
| L0Bridge | SoftBus ↔ MAVLink | FC | 50–100 | NED on wire | failsafe FC |

**Coordinate boundary (RECOMMENDATION):** SoftBus nav/facts in **ENU**; MAVLink to ArduPilot in **NED** at L0Bridge only.

---

## F. VIO / SLAM recommendation

| System | Backend | License | Maintenance signal | SoftBus wrap | Notes |
|--------|---------|---------|-------------------|--------------|-------|
| **OpenVINS** | MSCKF filter | GPL-3.0 | Active (community 2025) | Yes (C++ lib / process) | Clean VIO; loop optional |
| **ORB-SLAM3** | BA + multi-map | GPL-3.0 | Mature, slower cadence | Yes | Strong VO/VIO; heavier |
| **VINS-Fusion** | Ceres BA + GPS | GPL-3.0 | Reference; older commits | Yes | GPS fusion path useful |
| **Basalt** | square-root BA | **BSD-3** | Active | Yes | Better license for product |
| **Kimera-VIO** | GTSAM | BSD-2 | Active | Yes | Mesh side-product, heavier |
| **Isaac / cuVSLAM** | GPU | NVIDIA | Product stack | Possible | Jetson-oriented; evaluate Isaac ROS coupling |

Sources: [arXiv:2108.01654](https://ar5iv.labs.arxiv.org/html/2108.01654); OpenVINS paper Geneva et al.; engineering survey of drone VIO 2026 (license/maintenance table — treat as secondary to official repos); outdoor LC cost study [arXiv:2408.01716](https://doi.org/10.48550/arxiv.2408.01716).

**RECOMMENDATION:**  
- **Do not freeze** OpenVINS vs Basalt until bench + license policy. SoftBus contract: `/bd/nav/vio` via `IVioProvider` (`OpenVinsProvider` | `BasaltProvider`).  
- **FLIGHT-1 E2E (Det→Track→WorldFact)** does **not** require VIO — FC `NavState` + calibration is sufficient. VIO is P1 parallel track.  
- **Do not** put full ORB-SLAM3 mapping in the control loop until CPU budget proven.  
- Stereo+IMU preferred over mono for outdoor; mono+IMU only with excellent calibration.

**UNKNOWN:** NULLXES license policy for GPL in companion image — decide before shipping OpenVINS/ORB/VINS.

---

## G. Tracking recommendation

| Tracker | Strength | Airborne relevance |
|---------|----------|-------------------|
| **ByteTrack** | Strong association, high MOTA | No CMC |
| **BoT-SORT** | ByteTrack + better KF + **camera motion compensation** + optional ReID | **Best fit for moving UAV camera** |
| **OC-SORT** | Observation-centric under occlusion | Less CMC focus |

Source: [BoT-SORT arXiv:2206.14651](https://ar5iv.labs.arxiv.org/html/2206.14651); BoxMOT BoT-SORT docs (CMC options).

**RECOMMENDATION:** Primary tracker = **BoT-SORT (CMC on, ReID off first)**. Keep **IOU v1 as degraded/overbudget fallback** (fail-closed path). Output: `track_id`, image box, optional image-plane velocity → SceneFusion → WorldFact.

---

## H. Segmentation / depth recommendation

**SegFormer:** Still a **reasonable edge path in 2026** via NVIDIA TAO → ONNX → TensorRT (FP16; INT8 often unsupported for SegFormer in TAO Deploy). Official Jetson/DeepStream deploy path: [TAO SegFormer Deploy](https://docs.nvidia.com/tao/tao-toolkit/7.0.1/text/tao_deploy/segformer.html), [DeepStream SegFormer](https://docs.nvidia.com/tao/tao-toolkit/latest/text/ds_tao/segformer_ds.html). Prefer **SegFormer-B0** at 512², rate-limited (e.g. 5–10 Hz), not full cam rate.

**Alternatives (INFERENCE):** lighter CNN segmenters (PIDNet / DDRNet-class) may beat B0 on Jetson FPS — **NEEDS TEST** head-to-head on LoveDA/LandCover remap to CERBER surface classes.

**Depth / obstacle:**

| Approach | Weight/power | Reliability outdoor | Jetson cost |
|----------|--------------|---------------------|-------------|
| Stereo GS | med | good if baseline/calib solid | CPU/GPU moderate |
| Mono depth NN | low HW | domain-sensitive | GPU heavy |
| LiDAR (solid-state / mid-range) | higher W/mass | strong range | low GPU, driver work |
| Optical flow | low | ego-motion only | low |

**RECOMMENDATION:** FLIGHT-1 = **no LiDAR**; stereo **or** mono depth **offline eval** only. FLIGHT-2 = add **short-range depth** (stereo GS pair or light solid-state) for terrain/obstacle, fused as WorldFact `obstacle` with covariance.

---

## I. FC ↔ Companion contract

### FC baseline — SUPERSEDED (Matek H743-WING)

Research snapshot. **Flight-1 lock 2026-08-13:** Holybro Pixhawk 6C + M10 + PM. See [FLIGHT1_BOM_LOCK.md](FLIGHT1_BOM_LOCK.md). Do not buy H743-WING V3 as default (OEM catalog gone).

**Firmware for FLIGHT-1:** **ArduPilot Plane** target `Pixhawk6C`. Custom L0 only after ArduPilot path proven.

### Minimal safe MAVLink contract

**FC → Companion (telemetry):**  
`ATTITUDE` or `ATTITUDE_QUATERNION`; `LOCAL_POSITION_NED` / `GLOBAL_POSITION_INT`; `GPS_RAW_INT`; `SYS_STATUS` / `HEARTBEAT`; `SCALED_IMU` or `HIGHRES_IMU` when supported ([ArduPilot HIGHRES_IMU PR](https://github.com/ArduPilot/ardupilot/pull/27007) — verify version); `VFR_HUD`; `BATTERY_STATUS`.

**Companion → FC (guidance only) — FACT ArduPilot Plane (wing):**  
Do **not** use Copter Guided velocity semantics. Per [Plane Commands in Guided Mode](https://ardupilot.org/dev/docs/plane-commands-in-guided-mode.html):

| Intent | Plane contract |
|--------|----------------|
| Fly to lat/lon/alt | `MISSION_ITEM_INT` + `MAV_CMD_NAV_WAYPOINT` (16), `current=2` (guided goto) |
| Altitude only (local) | `SET_POSITION_TARGET_LOCAL_NED`, `MAV_FRAME_LOCAL_OFFSET_NED` (alt field; other fields unsupported) |
| Altitude (global) | `SET_POSITION_TARGET_GLOBAL_INT` with POSITION_TARGET_TYPEMASK bit 3 |
| Low-level attitude | `SET_ATTITUDE_TARGET` continuously; if missing > `GUIDED_TIMEOUT` → revert to previous fly-to |

Stack boundary: `SwarmIntent` → `GoalMsg` → Guidance → **`ArduPlaneAdapter`** → Plane Guided.  
**Never** bypass ArduPilot hard-realtime rate loop for servos from Python.

**Safety:** FC failsafes own GPS/radio loss; companion loss → FC RTL/LOITER; companion never arms without FC heartbeat.

**L0Bridge / ArduPlaneAdapter:** SoftBus ENU goals ↔ Plane MAVLink; stamp with FC `time_boot_ms` + estimated offset.

---

## J. SoftBus topic / interface proposal (additions)

Existing canon retained. Add:

| Topic | Msg | Notes |
|-------|-----|-------|
| `/bd/nav/vio` | pose, vel, cov, status | from VIO process |
| `/bd/nav/fused` | EKF out | GNSS+VIO+baro |
| `/bd/vision/seg` | class mask meta / ROI | low rate |
| `/bd/depth/points` or `/bd/depth/grid` | obstacle | optional |
| `/bd/calib/active` | hashes of calib files | fail-closed |
| `/bd/time/sync` | offsets cam/imu/fc | SensorHub |
| `/bd/l0/mavlink_health` | link, mode, failsafe | L0Bridge |

All messages: `stamp_ns` (monotonic) + `sensor_stamp_ns` + `frame_id`.

---

## K. Failure / degraded-state matrix

| Failure | Detect | Isolate | Degrade | Recover |
|---------|--------|---------|---------|---------|
| Camera lost / stale | frame age > T | Vision/POSEIDON off | nav GNSS+IMU; LOITER if no nav | reconnect driver |
| IMU stale | dt gap | VIO pause | GNSS+baro / RTB | resync |
| GNSS denied | fix_ok=false / cov↑ | mark GPS_DENIED | VIO-hold / SAFE_LOITER | reacquire |
| VIO diverge | cov / innovation | ignore VIO | GNSS-only | reset VIO |
| Detector crash | health | restart VisionService | last tracks TTL expire | watchdog |
| Tracker diverge | ID thrash metrics | reset tracks | IOU fallback | — |
| Overheat / GPU OOM | tegrastats / OOM | drop Seg→POSEIDON→imgsz | LOITER | cool / restart TRT |
| SoftBus congestion | queue depth | drop debug topics | keep l0/nav | — |
| Companion A fail | dual HB | switch B | DEGRADED_* | — |
| A/B disagree | mirror hash | freeze setpoint | SAFE_LOITER | operator |
| FC link loss | mav heartbeat | stop guided cmds | FC failsafe | reacquire |

Aligns with existing FM modes; expand health_flags.

---

## L. BOM (approximate street prices — verify quote)

Prices **approximate / region-dependent** (2026 retail signals). Mark **UNKNOWN** where not locked.

### BENCH
| Item | Model | Why | I/F | ~Price |
|------|-------|-----|-----|--------|
| Companion | Orin NX 16GB DevKit or x86+GPU | software bring-up | — | DevKit ~$900–1200; module alone ~$850–1450 ([retail spread](https://www.antratek.com/nvidia-jetson-orin-nx-16gb-module-1)) |
| Cam | USB3 global shutter (Imaging Source / Basler) | easy | USB3 | ~$300–800 |
| FC | Matek H743-WING V3 | UART bench | USB/UART | ~$60–90 |
| GNSS | M10/M9N module | nav | UART | ~$30–60 |
| PSU / bench harness | lab PSU | — | — | — |

### FLIGHT-1 (min real prototype)
| Item | Model | Why | I/F | ~W / mass | ~Price |
|------|-------|-----|-----|-----------|--------|
| SoM | **Orin NX 16GB** | Detect+track+fusion budget | SODIMM | 15–25W cruise (mode) | ~$1k module |
| Carrier | Orin NX carrier w/ CSI or GMSL, NVMe, UART | flight I/O | — | — | ~$200–600 |
| Cam | GS CSI **or** GMSL IMX5xx class | airborne CV | CSI/GMSL2 | ~1–2W | ~$200–500 + optics |
| Deserializer | TechNexion / e-con / Basler kit if GMSL | long cable | — | — | ~$100–400 |
| FC | Matek H743-WING V3 | ArduPilot Plane | UART TELEM | ~0.8W | ~$70 |
| GNSS+compass | Matek M10-5883 or CAN GPS | ArduPilot | UART/CAN | — | ~$40–80 |
| Cooling | active fan / heat pipe for NX | sustained TRT | — | — | ~$20–60 |
| Link | SiK / ELRS / Ethernet bridge | companion↔GCS | — | — | — |

### FLIGHT-2 (perception/VIO)
FLIGHT-1 plus: **stereo GS pair** or second cam; consider **AGX Orin 32GB** if Seg+VIO+dual detect concurrent; optional mid-range depth; PPS-capable GNSS; hardware sync trigger.

Exact mass/power of full stack = **NEEDS NULLXES airframe budget**.

---

## M. Performance acceptance criteria (measurable)

Lock on Orin NX 16GB, `nvpmodel` documented, cooler documented, JetPack version pinned:

| Metric | FLIGHT-1 target (proposal) | How |
|--------|----------------------------|-----|
| CERBER TRT FP16 imgsz640 | **p95 latency ≤ 40 ms**, sustained | host timer around ORT/TRT |
| End-to-end cam→WorldFact | **p95 ≤ 80 ms** | SensorHub stamp → fusion publish |
| Cam→setpoint (guided) | **p95 ≤ 120 ms** | exclude FC inner loop |
| Track rate | = detect rate, ID switch rate logged | MOT metrics on flight log |
| Dropped frames | **< 1%** over 30 min | SensorHub counters |
| SoftBus queue | max depth < N (e.g. 5) per critical topic | bus metrics |
| Tj | below NVIDIA slowdown (datasheet ~99°C SoC — verify) | tegrastats |
| Power | within chosen nvpmodel budget | INA / module rail |
| GNSS-denied hover/loiter | safe LOITER without guided chase | FM test |

No “real-time” without these numbers.

---

## N. Implementation roadmap

### P0
1. SensorHub: CSI/GMSL/V4L2 cam + MAVLink IMU/GNSS → SoftBus with stamps  
2. Calib YAML load + replace pixel→ENU stub (WorldFact + frame + cov)  
3. **ArduPlaneAdapter** (Plane Guided: MISSION_ITEM_INT goto / alt / optional attitude) + failsafe — not Copter velocity  
4. Onboard CERBER TRT engine + tegrastats harness  
5. POSEIDON uav pack export + router smoke on NX  
6. FLIGHT-1 props-off E2E: Det→Track→WorldFact→DMI→Goal (FC nav OK; **VIO not required**)  

### P1
7. BoT-SORT + CMC primary; IOU degraded fallback  
8. `IVioProvider` → `/bd/nav/vio` + NavEKF fuse (OpenVINS | Basalt by bench+license)  
9. Dual-compute live failover on real SensorHub/L0 I/O  
10. SceneAnalyst → TrackTarget auto (civil modes)  

### P2
10. SegFormer-B0 TRT rate-limited  
11. Stereo/depth obstacle facts  
12. POSEIDON fire/power packs  
13. PPS/HTE time sync if GNSS-denied accuracy required  

---

## O. Primary sources

- NVIDIA Jetson Orin: https://www.nvidia.com/en-us/autonomous-machines/embedded-systems/jetson-orin/  
- JetPack 6.2 Super Mode: https://developer.nvidia.com/blog/nvidia-jetpack-6-2-brings-super-mode-to-nvidia-jetson-orin-nano-and-jetson-orin-nx-modules/  
- Orin power guide: https://docs.nvidia.com/jetson/archives/r35.6.1/DeveloperGuide/SD/PlatformPowerAndPerformance/JetsonOrinNanoSeriesJetsonOrinNxSeriesAndJetsonAgxOrinSeries.html  
- YOLOv8 on Orin NX benchmark: https://doi.org/10.3390/computers15020074  
- Matek H743-WING manual: https://www.mateksys.com/downloads/H743-WING_Manual.pdf  
- ArduPilot MatekH743: https://github.com/ArduPilot/ardupilot_wiki/blob/master/common/source/docs/common-matekh743-wing.rst  
- ArduPilot Plane Guided MAVLink: https://ardupilot.org/dev/docs/plane-commands-in-guided-mode.html  

- Kalibr cam-IMU: https://github.com/ethz-asl/kalibr/wiki/Camera-IMU-calibration  
- BoT-SORT: https://ar5iv.labs.arxiv.org/html/2206.14651  
- OpenVINS / SLAM compare: https://ar5iv.labs.arxiv.org/html/2108.01654  
- SegFormer TAO/TRT: https://docs.nvidia.com/tao/tao-toolkit/7.0.1/text/tao_deploy/segformer.html  
- e-con IMX568 GMSL: https://www.e-consystems.com/nvidia-cameras/jetson-agx-orin-cameras/imx568-5mp-gmsl2-global-shutter-camera.asp  
- TechNexion GMSL Orin: https://www.technexion.com/products/serdes/gmsl/gmsl2-frame-grabber/vl-gm2-8cam-rpi22/  

---

## WHAT NULLXES NEEDS TO PROVIDE

Cannot be determined by web search alone:

1. **Exact companion SKU** — Orin NX 8 vs 16 vs AGX; carrier board part number  
2. **Camera shortlist lock** — CSI vs GMSL, sensor, lens FOV, mass, IP rating  
3. **Mount geometry** — camera→body R,t; lever arms GNSS/antenna; IMU location (FC vs companion)  
4. **FC revision** — H743-WING V2 vs V3 (IMU part numbers differ)  
5. **Firmware choice** — ArduPilot Plane vs PX4 vs custom L0 legal/ops decision  
6. **Airframe** — BWB/wing span, cruise speed, altitude, vibration environment  
7. **Power budget** — watts available for companion at cruise; battery chemistry  
8. **Mass budget** — grams left for companion+cam+cooling  
9. **Target rates** — required detect FPS, VIO rate, max altitude AGL for fusion  
10. **License policy** — OK to ship GPL (OpenVINS/ORB) on companion image?  
11. **Dataset status** — Seraphim/DUT/FLAME/InsPLAD on disk; train farm schedule  
12. **Link architecture** — radio type, whether GSC is airborne or ground-only  
13. **Dual-compute** — one Orin or two virtual channels on one SoM for Alpha  
14. **Existing calib data** — any Kalibr bags already  
15. **Ops envelope** — day-only vs night → IR later (Anti-UAV410)

Provide items **1–6 + 9–10** to freeze FLIGHT-1 design.
