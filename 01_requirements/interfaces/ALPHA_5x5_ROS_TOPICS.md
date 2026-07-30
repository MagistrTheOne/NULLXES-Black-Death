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
| `/bd/dual/mirror` | on significant change (event-driven preferred) |

## DMI v1 (L6 — not L0)

Event-driven. L0 must not subscribe to these topics.

| Topic | Direction | Notes |
|-------|-----------|-------|
| `/bd/dmi/intent` | coordinator → agent | SwarmIntent |
| `/bd/dmi/task_offer` | coordinator → one agent | exclusive offer |
| `/bd/dmi/task_claim` | agent → coordinator | ACCEPT / REJECT |
| `/bd/dmi/agent_status` | agent → coordinator | pose, SOC, health_factor |
| `/bd/dmi/world_fact` | any → peers | Shared World Cache fact |
| `/bd/dmi/swarm_health` | agent view | ONLINE…RECOVERED |

Accepted intent bridges to `/bd/planning/goal` for guidance. Canon: `00_docs/adr/ADR-002_DMI_V1.md`.

Digital twin must reuse these names: `07_simulation/digital_twin/topic_map.yaml`.
