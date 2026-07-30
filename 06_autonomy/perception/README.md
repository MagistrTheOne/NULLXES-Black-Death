# NULLXES CERBER — perception

Onboard sensing → scene understanding. **CERBER** is the perception *system*, not a single network.  
Canon: [`00_docs/architecture/CERBER.md`](../../00_docs/architecture/CERBER.md)

```
CERBER
├── Vision          OpenCV · letterbox
├── Detection       YOLO → ONNX Runtime
├── Tracking        (lane — not Alpha-critical)
├── Classification  detect classes / later heads
├── Segmentation    (lane)
├── Multi-Sensor Fusion   GNSS+IMU EKF · LiDAR later
└── Obstacle / scene recognition → bus / DMI facts
```

| Package | CERBER lane | Status |
|---------|-------------|--------|
| `vision/` | Vision + Detection | Algorithm ready; **BLOCKED** without real ONNX + sha256 |
| `fusion/` | Multi-Sensor Fusion | Algorithm ready; needs real IMU/GNSS |
| `sensors/` | ingest adapters | **BLOCKED** — no drivers yet |
| `slam/` | map / VIO | **BLOCKED** Alpha Flight-1 |

IMU bus contract: `ImuMsg.accel_mps2` = linear acceleration ENU, gravity removed by the driver.  
No mocks. Missing hardware → **BLOCKED** + exact dependency.
