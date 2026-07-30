# Стек — зафиксировано (rev B)

## Host / languages

| Слой | Язык | Где |
|------|------|-----|
| High-level | **Python 3.11** | `06_autonomy`, sim orchestration, aero/structure scripts, CI helpers |
| Realtime L0 | **C++17/20** | `05_avionics` — inner-loop, drivers, buses, timing |
| Middleware | **ROS 2 Jazzy+** | сообщения между Python↔C++; Win11 binary; Gazebo — WSL2 |

**Rust на Alpha не используем.** Только Python 3.11 + C++.

## Симуляция и анализ

| Область | Инструмент |
|---------|------------|
| Симуляция | Gazebo (WSL2), AirSim |
| CFD | OpenFOAM / SU2 |
| Предварительная аэродинамика | XFOIL / XFLR5 |
| Структура / аэроупругость | CalculiX / Code_Aster |
| Aeroelasticity | Bisplinghoff & Ashley; Dowell; Doublet Lattice; flutter/divergence |

## Автономия — запреты

- Нет облачных LLM / внешних API в полёте
- Модели: только локальный ONNX в `06_autonomy/models/onnx/`

## Граница Python ↔ C++

```
[06_autonomy Python]  perception / planning / BT / FM / dual_compute
         │  ROS 2 topics/services (setpoints, health, nav)
         ▼
[05_avionics C++]     hard realtime inner-loop, actuators, IMU drivers
```

Как писать код по слоям: `00_docs/conventions/HOW_TO_WRITE.md`.
