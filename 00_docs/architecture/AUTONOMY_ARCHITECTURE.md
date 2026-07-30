# Архитектура автономного ИИ — BLACK DEATH

Платформа: civil BWB ~50×50 м.  
Принцип: высокая избыточность + graceful degradation (философия распределённого управления / многоканальности, гражданское применение).

## Слои

```
┌─────────────────────────────────────────────────────────────┐
│  L5  MISSION / BEHAVIOUR                                     │
│      planning/missions + planning/behaviour (AlphaBT)        │
│      цели civil: logistics | energy | disaster | construction│
└────────────────────────────┬────────────────────────────────┘
                             │ mission goals / mode
┌────────────────────────────▼────────────────────────────────┐
│  L4  PLANNING                                                │
│      planning/trajectory — коридоры, waypoints, constraints  │
└────────────────────────────┬────────────────────────────────┘
                             │ trajectory / setpoints (outer)
┌────────────────────────────▼────────────────────────────────┐
│  L3  CORE DECISION + STATE                                   │
│      core/state · core/decision · core/health                │
│      арбитраж: mission vs fault vs safety envelopes          │
└───────────────┬─────────────────────────────┬───────────────┘
                │                             │
┌───────────────▼───────────────┐ ┌───────────▼───────────────┐
│  L2a PERCEPTION               │ │  L2b FAULT MANAGEMENT     │
│  vision → YOLO/ONNX           │ │  detect → isolate →       │
│  sensors → fusion (EKF/UKF)   │ │  reconfigure              │
│  slam (OpenVINS/ORB-SLAM3)    │ │  degradation modes        │
└───────────────┬───────────────┘ └───────────┬───────────────┘
                │ world + nav state           │ health / mode
┌───────────────▼─────────────────────────────▼───────────────┐
│  L1  GUIDANCE / CONTROL BRIDGE                               │
│      control/guidance → setpoints в 05_avionics inner-loop   │
└────────────────────────────┬────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────┐
│  L0  REALTIME AVIONICS (C++17/20)                            │
│      05_avionics — inner-loop, buses, actuators, timing      │
└─────────────────────────────────────────────────────────────┘
```

Middleware между L1–L5: **ROS 2**.  
Языки Alpha: **Python 3.11 + C++** (Rust не используем).  
Модели: только `06_autonomy/models/onnx/` (+ configs).

## Потоки данных (кратко)

1. Сенсоры → `perception/sensors` → `fusion` / `slam` / `vision`
2. Оценка состояния → `core/state`
3. Детекции объектов/сцены → `planning` + `core/decision`
4. Fault signals → `fault_management` → `core/health` → `core/decision`
5. Decision → trajectory/guidance → L0 setpoints
6. L0 telemetry/health → обратно в fusion и FM

## Избыточность и graceful degradation

### Compute

- Минимум **2 независимых compute-канала** для autonomy (A/B).
- Primary ведёт decision; Secondary — hot/warm standby с зеркалом state.
- Failover: FM переключает канал; mission mode → degrade (упрощённый план / return-to-base / safe loiter — civil modes, детали в `01_requirements`).

### Perception

- Разнесённые сенсорные комплекты (геометрия BWB позволяет).
- Fusion не зависит от одного сенсора: потеря камеры/IMU/GNSS → пересчёт ковариаций, сужение конверта.
- YOLO/ONNX: при потере GPU — CPU ORT с пониженным FPS и урезанным набором классов.

### Control path

- Guidance (Python) выдаёт setpoints; inner-loop (C++) **не зависит** от Python для стабилизации.
- При смерти autonomy high-level: L0 удерживает последний валидный safe mode / preloaded contingency (определяется requirements).

### Decision

- Mode policy (`AlphaBT`) с явными **degraded branches** (полная миссия → ограниченная → безопасное завершение).
- Ни один отказ одиночного модуля не должен требовать «облачного» решения.

## Границы ответственности

| Что | Где |
|-----|-----|
| Hard realtime ≤ цикл inner-loop | `05_avionics` (C++) |
| Perception, planning, BT, FM | `06_autonomy` |
| Веса моделей | `06_autonomy/models/` |
| Сценарии проверки | `07_simulation` + `10_tests` |

## Запреты в архитектуре

- Нет внешнего LLM/API в decision path
- Нет обязательной связи с землёй для продолжения полёта в degraded mode
- Нет единой точки отказа на одном compute / одном сенсорном канале без FM-ответа
