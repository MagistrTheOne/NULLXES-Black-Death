# CERBER perception code

Canon stack: `00_docs/architecture/CERBER_VISION_STACK.md`

| Dir | Layer | Status |
|-----|-------|--------|
| `vision/` | preprocess + **L1 Detect** ONNX | shipped (letterbox, session, decode) |
| `segmentation/` | **L2 Segment** | TODO — SegFormer service |
| `tracking/` | **L3 Track** | TODO — BoT-SORT |
| `navigation/` | **L4 Nav** decision aids | TODO — OpenLander trial |
| `fusion/` | Nav EKF + future **L5** CV scene fusion | EKF partial |
| `sensors/` | adapters | stubs / BLOCKED without HW |
| `slam/` | optional | README only |

Weights/configs: `../models/`. Mission consumer: `../dmi/`.
