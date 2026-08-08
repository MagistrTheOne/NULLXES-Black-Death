# CERBER perception code

Canon: `00_docs/architecture/CERBER_VISION_STACK.md` · Status SoT: `00_docs/architecture/REPO_STATUS_MAP.md`

| Dir | Layer | Status |
|-----|-------|--------|
| `vision/` | L1 Detect ONNX (CERBER) | **HAS_CODE** — needs live cam + engine on target |
| `sensors/` | SensorHub cam + FC IMU/GNSS | **HAS_CODE** v1 |
| `calibration/` | Intrinsics/extrinsics loader | **HAS_CODE** — bench YAML in `../calib/` |
| `tracking/` | BoT-SORT + IOU degraded fallback | **HAS_CODE** |
| `fusion/` | SceneFusion WorldFact + EKF + nav_fuse + SceneAnalyst | **HAS_CODE** |
| `segmentation/` | SegFormer SoftBus service | **HAS_CODE shell** — no weights → `ok=false` |
| `depth/` | Obstacle grid service | **HAS_CODE shell** — FLIGHT-2 |
| `slam/` | `IVioProvider` (OpenVINS/Basalt) | **Contract** — native lib not linked (`degraded`) |
| `qr/` | CERBER RT QR | **absent** — wait ADR-003 |
| `navigation/` | OpenLander / crawl aids | **absent** |

Weights: `../models/onnx/detector_alpha*.onnx` · POSEIDON packs: `../models/poseidon/packs/` (manifests; ONNX pending).  
Mission consumer: `../dmi/`. SoftBus nodes: `../ros2/nodes/`.
