# Dual-compute autonomy — ALPHA 5×5

**Status:** architecture draft v0  
**Baseline:** 2 независимых канала A/B · onboard only · ROS 2 Jazzy+  
**Refs:** `00_docs/architecture/AUTONOMY_ARCHITECTURE.md` · `01_requirements/ALPHA_5x5_REQUIREMENTS.md`

## 1. Channels

| | Channel A | Channel B |
|---|-----------|-----------|
| Role | Primary (default) | Secondary (hot/warm standby) |
| Compute | независимый SBC/SoC | независимый SBC/SoC |
| Power | dual-feed rail A | dual-feed rail B |
| Autonomy | L1–L5 Python 3.11 | зеркало L1–L5 |
| Models | локальный ONNX | копия ONNX |
| Sensors | полный комплект (share via bus) | полный комплект (share via bus) |
| Output | guidance setpoints → L0 | setpoints при takeover |

L0 (inner-loop) — **отдельный realtime** (`05_avionics`), принимает setpoints от активного канала; не умирает при падении Python.

## 2. Topology

```
 cameras/IMU/GNSS/LiDAR
          │
     sensor bus / ROS 2
      ┌───┴────┐
      ▼        ▼
  Compute A  Compute B
  (primary)  (standby)
      │        │
      └───┬────┘
          ▼
   Cross-channel link
   (heartbeat + state mirror)
          │
          ▼
     L0 Flight Control
     (C++ realtime)
          │
     actuators / ESC
```

## 3. State mirror

Минимальный пакет (каналы A↔B, ≥10 Hz):

| Field | Content |
|-------|---------|
| `stamp` | time sync |
| `nav_state` | pose, vel, cov |
| `mission_mode` | BT mode / mission id |
| `health` | FM flags |
| `active` | who commands L0 |
| `setpoint_hash` | целостность последнего SP |

Сериализация: msgpack или ROS 2 custom msg (`06_autonomy/ros2/`).

## 4. Failover rules

| Event | Action |
|-------|--------|
| Heartbeat A lost > T_hb | B → active; mode DEGRADED_COMPUTE |
| FM isolates A | B → active |
| A и B healthy | A active; B mirrors |
| Оба деградированы | L0 contingency / SAFE_LOITER / RTB |

\(T_{hb}\) — **150 ms** peer timeout (code); takeover budget ≤ **500 ms**.

## 5. Process map (каждый канал)

| Process | Path | Notes |
|---------|------|-------|
| state | `core/state` | **BLOCKED** — not implemented |
| decision | `core/decision` | **BLOCKED** — FM+AlphaBT cover Alpha |
| vision | `perception/vision` | OpenCV + ONNX YOLO |
| fusion | `perception/fusion` | filterpy EKF |
| slam | `perception/slam` | **BLOCKED** Alpha Flight-1 |
| behaviour | `planning/behaviour` | AlphaBT mode policy |
| trajectory | `planning/trajectory` | **BLOCKED** — not implemented |
| guidance | `control/guidance` | → L0 |
| FM | `fault_management/*` | detect/isolate/reconfigure |
| dual_compute | `core/dual_compute` | heartbeat, election, mirror |

## 6. Package layout (skeleton)

```
06_autonomy/core/dual_compute/
  README.md          ← pointer
  channel_config.yaml
  heartbeat.py
  state_mirror.py
  active_election.py
```

## 7. Constraints

- Нет внешних API  
- Одинаковые ONNX на A и B  
- Сенсоры не «принадлежат» одному каналу без пути к другому  
- Graceful degradation ветки в BT обязательны  

## 8. Next implementation

1. Заполнить skeleton Python modules  
2. ROS 2 msgs + nodes в `06_autonomy/ros2/`  
3. HIL сценарий failover в `07_simulation/hil/` + `10_tests/hil/`
