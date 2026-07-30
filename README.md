# NULLXES BLACK DEATH

Гражданская инфраструктурная летающая платформа (flying wing / BWB).  
**Alpha 5×5 = System Architecture Demonstrator** (не endurance-демо). Канон: `[00_docs/adr/ADR-001_ALPHA_ARCHITECTURE_DEMONSTRATOR.md](00_docs/adr/ADR-001_ALPHA_ARCHITECTURE_DEMONSTRATOR.md)` · линии: `[00_docs/PRODUCT_LINES.md](00_docs/PRODUCT_LINES.md)`.

Назначение продукта: logistics · energy & grid · disaster response · construction · transportation · infrastructure.

**Запрещено:** любое упоминание вооружения, боевых сценариев и военного применения.

## Стек (зафиксирован)


| Слой                                  | Технология                                              |
| ------------------------------------- | ------------------------------------------------------- |
| Host                                  | **Windows / Linux**                                     |
| High-level / AI / sim / scripts       | **Python 3.11**                                         |
| Realtime L0 (flight control, drivers) | **C++17/20**                                            |
| Middleware                            | ROS 2 (Jazzy+) — Win/Linux; Gazebo на Linux (WSL2@Win)  |
| Autonomy inference                    | ONNX Runtime (+ TensorRT / OpenVINO при наличии железа) |
| VCS / CI                              | Git · colcon · GitHub Actions                           |


Автономный ИИ — **полностью onboard**, без внешних API и облака.  
Восприятие: **NULLXES CERBER** — `[00_docs/architecture/CERBER.md](00_docs/architecture/CERBER.md)`.  
Как писать код (CV, sim, L0): `[00_docs/conventions/HOW_TO_WRITE.md](00_docs/conventions/HOW_TO_WRITE.md)`.  
Production-first : `[00_docs/conventions/PRODUCTION_FIRST.md](00_docs/conventions/PRODUCTION_FIRST.md)`.

## Структура

```
00_docs/                 документация, архитектура, ADR
01_requirements/         миссии, ограничения, интерфейсы, safety
02_aerodynamics/         CFD, профили, аэроупругость, нагрузки
03_structure/            силовая схема, FEA, материалы, шасси
04_propulsion_energy/    тяга, энергосистема, распределение, тепло
05_avionics/             железо, драйверы, FSW, шины, timing
06_autonomy/             ГЛАВНЫЙ блок — локальный автономный ИИ
07_simulation/           Gazebo/AirSim, цифровой двойник, HIL
08_prototypes/           масштабируемые прототипы и стенды
09_manufacturing/        композиты, оснастка, сборка, QA
10_tests/                unit / integration / HIL / flight / regression
99_tools/                CI, скрипты, colcon, lint
```

Канон и детали: `[00_docs/](00_docs/)`.  
Партнёрам (50×50 + 5×5 + схема ИИ): `[00_docs/architecture/PARTNER_FAMILY_ARCHITECTURE.md](00_docs/architecture/PARTNER_FAMILY_ARCHITECTURE.md)`.  
Схема мозга: `[00_docs/architecture/BRAIN_SCHEME.md](00_docs/architecture/BRAIN_SCHEME.md)`.
