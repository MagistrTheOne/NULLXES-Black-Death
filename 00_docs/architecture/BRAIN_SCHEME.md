# Схема мозга — NULLXES autonomy

**Платформы:** BLACK DEATH (~50×50) · Black Judgment (5×5 Alpha)  
**Принцип:** onboard only · dual-compute · graceful degradation · civil modes  
**Стек:** Python 3.11 (L1–L5) · C++ (L0) · ROS 2 · ONNX  

Канон: [AUTONOMY_ARCHITECTURE](./AUTONOMY_ARCHITECTURE.md) · [PARTNER_FAMILY](./PARTNER_FAMILY_ARCHITECTURE.md) · [DMI_V1](./DMI_V1.md) · [ADR-002](../adr/ADR-002_DMI_V1.md)

---

## 1. Мозг целиком (слои)

```mermaid
flowchart TB
  subgraph DMI["L6 DMI — Distributed Mission Intelligence"]
    GSC["GroundSwarmCoordinator<br/>tasks / sectors / MissionScore"]
    L6["SwarmAgent<br/>ACCEPT REJECT facts"]
  end

  subgraph CORTEX["КОРА — миссия и решение"]
    L5["L5 Mission / Behaviour<br/>AlphaBT · civil goals"]
    L4["L4 Planning<br/>corridor / goal"]
    L3["L3 Decision + State<br/>mission ↔ fault ↔ envelope"]
  end

  subgraph SENSORY["СЕНСОРИКА — восприятие"]
    L2a["L2a Perception<br/>YOLO/ONNX · EKF · SLAM*"]
  end

  subgraph IMMUNE["ИММУНИТЕТ — отказы"]
    L2b["L2b Fault Management<br/>detect → isolate → reconfigure"]
  end

  subgraph MOTOR["МОТОРНЫЙ КОНТУР"]
    L1["L1 Guidance<br/>setpoints"]
    L0["L0 Inner-loop C++<br/>swarm-blind"]
  end

  GSC --> L6
  L6 -->|"SwarmIntent → GoalMsg"| L5
  L5 --> L4 --> L3
  L2a --> L3
  L2b --> L5
  L2b --> L3
  L3 --> L1 --> L0
```

\* SLAM — BLOCKED на Alpha Flight-1; EKF + vision работают по готовности драйверов/ONNX.  
DMI: L0 не знает про рой; см. [DMI_V1](./DMI_V1.md).

---

## 2. Полушария A / B (dual-compute)

```mermaid
flowchart LR
  subgraph WORLD["Мир"]
    CAM["Cameras ×4"]
    IMU["IMU ×2"]
    GNSS["GNSS"]
    LID["LiDAR"]
  end

  subgraph A["Compute A · primary"]
    PA["Perception + FM + BT<br/>Guidance"]
  end

  subgraph B["Compute B · standby"]
    PB["Зеркало стека<br/>hot/warm"]
  end

  subgraph STEM["Ствол — L0"]
    FC["Flight Control C++<br/>inner-loop всегда жив"]
  end

  WORLD --> A
  WORLD --> B
  A <-->|"heartbeat ≤150 ms<br/>state mirror"| B
  A -->|"active setpoints"| FC
  B -.->|"takeover ≤500 ms"| FC
  FC --> ACT["Elevons + motors"]
```

Оба полушария видят сенсоры. Командует L0 только **active**. При смерти коры L0 держит hold / contingency.

---

## 3. Потоки данных (что чем питается)

```mermaid
flowchart TB
  CAM["/bd/cam/*"] --> YOLO["Vision<br/>YOLOv8 → ONNX"]
  YOLO --> DET["/bd/vision/detections"]
  YOLO --> VH["/bd/vision/health"]

  IMU["/bd/l0/imu"] --> EKF["Nav EKF"]
  GNSS["/bd/gnss/fix"] --> EKF
  EKF --> NAV["/bd/nav/state"]

  VH --> FM["FM + AlphaBT"]
  LH["/bd/l0/health"] --> FM
  SOC["/bd/power/battery_soc"] --> FM
  HB["heartbeats A/B"] --> FM
  FM --> MODE["/bd/fm/mode"]

  NAV --> GUID["Guidance"]
  GOAL["/bd/planning/goal"] --> GUID
  MODE --> GUID
  ACTV["/bd/dual/active"] --> GUID
  GUID --> SP["/bd/l0/setpoint"]
  SP --> L0["L0 C++"]
  L0 --> ACT["/bd/l0/actuators"]
```

---

## 4. Режимы поведения (civil)

```mermaid
stateDiagram-v2
  [*] --> NOMINAL
  NOMINAL --> DEGRADED_SENS: cams / IMU / GNSS / LiDAR
  NOMINAL --> DEGRADED_PROP: 1 thruster
  NOMINAL --> DEGRADED_COMPUTE: peer lost
  NOMINAL --> RTB: battery low
  NOMINAL --> SAFE_LOITER: critical / nav fail

  DEGRADED_SENS --> NOMINAL: recovered
  DEGRADED_PROP --> RTB: envelope tight
  DEGRADED_COMPUTE --> NOMINAL: peer back
  RTB --> SAFE_LOITER: critical
  SAFE_LOITER --> [*]: land when site OK
```

---

## 5. Vision «глаз» (цифры)

```mermaid
flowchart LR
  BGR["BGR frame"] --> LB["letterbox 640×640"]
  LB --> ORT["ONNX Runtime<br/>images → output0"]
  ORT --> DEC["decode yolo_v8_raw<br/>1 × 4+nc × N"]
  DEC --> NMS["NMS iou=0.45"]
  NMS --> OUT["Detection[]<br/>conf≥0.35"]
```

| | |
|--|--|
| Классы (5) | person · vehicle · landing_pad · obstacle · cargo |
| Веса | `models/onnx/detector_alpha.onnx` + sha256 |
| Train | offline Ultralytics; в полёте только ONNX |

---

## 6. Карта «органов» → папки репо

| Орган | Слой | Путь |
|-------|------|------|
| Глаза | L2a vision | `06_autonomy/perception/vision/` |
| Вестибулярный / nav | L2a fusion | `06_autonomy/perception/fusion/` |
| Иммунитет | L2b | `06_autonomy/fault_management/` |
| Поведение | L5 | `06_autonomy/planning/behaviour/` |
| Моторика outer | L1 | `06_autonomy/control/guidance/` |
| Моторика inner | L0 | `05_avionics/flight_software/` |
| Полушария | dual | `06_autonomy/core/dual_compute/` |
| DMI / L6 | mission collective | `06_autonomy/dmi/` |
| Синапсы | bus | ROS 2 / `soft_bus` |

---

## 7. Одной фразой

> Сенсоры → восприятие + иммунитет → режим (AlphaBT) → guidance → **C++ L0**.  
> Два полушария A/B; ствол мозга (L0) не умирает вместе с Python.  
> DMI (L6) раздаёт задачи/секторы; **L0 swarm-blind**.
