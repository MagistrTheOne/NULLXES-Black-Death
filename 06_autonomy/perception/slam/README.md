# VIO / SLAM

**Status:** SoftBus contract HAS_CODE — native OpenVINS/Basalt NOT linked (uninit slots).

- `NullVioProvider` — always `uninit`
- `OpenVinsProvider` / `BasaltProvider` — deploy slots, `uninit` until native (OpenVINS is GPL-3, not a product default)
- `NullxesVoProvider` (`provider=nullxes_vo`) — LK optical flow + IMU only if accel ≠ 0
- Soft node: `ros2/nodes/vio_soft.py` default `nullxes_vo` → `/bd/nav/vio` + `/bd/nav/fused`
- Fuse: `uninit` / `degraded` / `diverge` → FC-only
