# Soft bus / ROS 2 — ALPHA 5×5 (production-first)

**SoftBus** (`06_autonomy/soft_bus/`) — in-process pub/sub transport abstraction with canon topic names.  
**bd_interfaces** — ROS 2 `.msg` mirror for colcon when ROS is installed.

## Policy

No mocks, stubs, dummy weights, fake sensors, or invented telemetry.

| Artifact | Status |
|----------|--------|
| Topic contracts / dataclasses / `.msg` | shipped |
| Algorithms (EKF, BT, FM, YOLO decode, guidance, dual election, L0 gains) | shipped |
| Nodes on SoftBus | ship; **fail BLOCKED** if required weights/drivers missing |
| Sensor simulation / dummy ONNX / soft twin fakes | **removed** |

## BLOCKED runtime until

1. Real cameras publishing `/bd/cam/*` (drivers)
2. Real IMU `/bd/l0/imu` and GNSS `/bd/gnss/fix`
3. Real ONNX at `models/onnx/detector_alpha.onnx` + `sha256` in config (`export_yolo_onnx.py`)
4. Dual-compute peers exchanging heartbeat on real network (or same-host processes with real I/O)

Topic contract: `01_requirements/interfaces/ALPHA_5x5_ROS_TOPICS.md`
