# VIO / SLAM

**Status:** SoftBus contract HAS_CODE — native OpenVINS/Basalt NOT linked

- `ivio.IVioProvider` — SoftBus interface
- `OpenVinsProvider` / `BasaltProvider` — deploy wrappers (status=`degraded` until native backend)
- Soft node: `ros2/nodes/vio_soft.py` → `/bd/nav/vio` + `/bd/nav/fused`

Winner chosen by onboard bench + GPL policy (see ONBOARD_PERCEPTION_RESEARCH).
