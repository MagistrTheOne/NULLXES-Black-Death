# Perception

Onboard sensing → estimates. No mocks. Missing hardware → **BLOCKED**.

| Package | Role | Status |
|---------|------|--------|
| `vision/` | YOLO ONNX detect | Algorithm ready; **BLOCKED** without real ONNX + sha256 |
| `fusion/` | GNSS+IMU EKF | Algorithm ready; needs real IMU/GNSS on bus |
| `sensors/` | Camera / IMU / GNSS / LiDAR adapters | **BLOCKED** — no drivers yet |
| `slam/` | Visual-inertial / lidar SLAM | **BLOCKED** — not selected for Alpha Flight-1 |

IMU bus contract: `ImuMsg.accel_mps2` is **linear acceleration ENU**, gravity removed by the driver.
