# ALPHA 5×5 — ROS 2 topic map (L0 ↔ autonomy)

**Middleware:** ROS 2 Jazzy+ · QoS: sensor data Best Effort; commands Reliable

## Autonomy → L0

| Topic | Type (logical) | Rate | Notes |
|-------|----------------|------|-------|
| `/bd/l0/setpoint` | attitude+thrust setpoint | 50 Hz | roll, pitch, yaw_rate, thrust_norm, valid |
| `/bd/dual/active` | string `A`\|`B` | on change + 1 Hz | who may command |
| `/bd/fm/mode` | string mode enum | on change | NOMINAL…RTB |

## L0 → Autonomy

| Topic | Type (logical) | Rate | Notes |
|-------|----------------|------|-------|
| `/bd/l0/imu` | imu | 200–500 Hz | primary bus sample |
| `/bd/l0/actuators` | elevon+motor feedback | 50 Hz | |
| `/bd/l0/health` | bitflags | 10 Hz | ESC/IMU/bus |

## Perception / nav (autonomy internal)

| Topic | Rate |
|-------|------|
| `/bd/cam/forward`, `/down`, `/left`, `/right` | 30 Hz |
| `/bd/lidar/scan` | ≥10 Hz |
| `/bd/gnss/fix` | 5–10 Hz |
| `/bd/nav/state` | 50 Hz |
| `/bd/vision/detections` | 10–30 Hz |
| `/bd/vision/health` | 2 Hz |

## Dual-compute

| Topic | Rate |
|-------|------|
| `/bd/dual/heartbeat_A`, `/bd/dual/heartbeat_B` | 50 Hz |
| `/bd/dual/mirror` | 20 Hz |

Digital twin must reuse these names: `07_simulation/digital_twin/topic_map.yaml`.
