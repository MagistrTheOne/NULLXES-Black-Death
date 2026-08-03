# CERBER perception code

Canon stack: `00_docs/architecture/CERBER_VISION_STACK.md` · Robot: `00_docs/architecture/CERBER_RT.md`

| Dir | Layer | Status |
|-----|-------|--------|
| `vision/` | preprocess + **L1 Detect** ONNX (aerial + RT session) | shipped (letterbox, session, decode) |
| `qr/` | **CERBER RT** QR decoder | planned — see CERBER_RT |
| `segmentation/` | **L2 Segment** | planned — SegFormer service |
| `tracking/` | **L3 Track** | planned — BoT-SORT |
| `navigation/` | **L4 Nav** decision aids | planned — OpenLander / RT crawl |
| `fusion/` | Nav EKF + CV / proximity fusion | EKF partial; RT proximity planned |
| `sensors/` | adapters | stubs / BLOCKED without HW |
| `slam/` | optional | README only |

Weights/configs: `../models/` (`detector_alpha*.yaml` aerial · `detector_rt_v1.yaml` robot).  
Mission consumer: `../dmi/`.
