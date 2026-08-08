# Sensors / SensorHub

**Status:** HAS_CODE (v1)

- `camera_source.OpenCvCameraSource` — V4L2 / CSI / USB via OpenCV
- `fc_telemetry` + `mavlink_link.MavlinkFcLink` — ArduPilot Plane telemetry → ENU SoftBus
- `sensor_hub.SensorHub` — publishes `/bd/cam/*`, `/bd/l0/imu`, `/bd/gnss/fix`, `/bd/nav/state` (FC), `/bd/time/sync`, `/bd/sensorhub/health`

Soft node: `ros2/nodes/sensor_hub_soft.py`

Production path uses real devices or HIL MAVLink. Unit tests inject `FcTelemetry` via `SensorHub.ingest_fc` (no fake publishers inside the hub).
