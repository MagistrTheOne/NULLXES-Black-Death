# Назначение папок — NULLXES BLACK DEATH

## Корневые блоки

| Папка | Назначение |
|-------|------------|
| `00_docs/` | Канон проекта: архитектура, стек, соглашения, ADR. Единственный источник истины по «как устроено». |
| `01_requirements/` | Миссии (civil only), жёсткие ограничения, внешние/внутренние интерфейсы, safety requirements. |
| `02_aerodynamics/` | CFD (OpenFOAM/SU2), профили (XFOIL/XFLR5), аэроупругость (flutter/divergence), аэродинамические нагрузки. |
| `03_structure/` | Силовая схема BWB, FEA (CalculiX/Code_Aster), материалы, шасси, load paths. |
| `04_propulsion_energy/` | Распределённая тяга, накопители, power distribution, тепловой контур. |
| `05_avionics/` | Авионика: hardware, драйверы, realtime FSW (C++ only), шины, синхронизация времени. |
| `06_autonomy/` | **Главный блок.** Onboard ИИ: perception → fusion → planning → control + fault management. Без внешних API. |
| `07_simulation/` | Цифровой двойник: Gazebo (WSL2), AirSim, сценарии, HIL. |
| `08_prototypes/` | Масштабируемые модели, авионика-стенды, subsystem rigs. |
| `09_manufacturing/` | Композиты, оснастка, сборка, QA производства. |
| `10_tests/` | Unit, integration, HIL, лётные/наземные испытания, regression. |
| `99_tools/` | CI (GitHub Actions), colcon-обёртки, lint, утилиты. |

## `06_autonomy/` (детально)

| Подпапка | Назначение |
|----------|------------|
| `core/` | Ядро решений: state, health, decision arbitration, внутренние интерфейсы слоёв. |
| `core/decision/` | Арбитраж режимов, выбор поведения при конфликтах целей/отказов. |
| `core/state/` | Единое состояние платформы (vehicle + mission + health). |
| `core/health/` | Health monitoring агрегация для autonomy. |
| `core/interfaces/` | Контракты между perception / planning / control / fault. |
| `perception/` | **NULLXES CERBER** — perception system (vision, detect, fusion, …). |
| `perception/vision/` | CERBER Vision + Detection: OpenCV + YOLO→ONNX Runtime. |
| `perception/sensors/` | Драйверы/адаптеры сенсоров (не realtime HAL — тот в `05_avionics`). |
| `perception/fusion/` | CERBER Multi-Sensor Fusion: EKF/UKF. |
| `perception/slam/` | OpenVINS / ORB-SLAM3 где применимо. |
| `planning/missions/` | Миссионные планы civil infrastructure. |
| `planning/trajectory/` | Траектории, коридоры, ограничения. |
| `planning/behaviour/` | Flight-mode policy (`AlphaBT`) — degraded / RTB / loiter. |
| `control/guidance/` | Guidance (внешний контур). |
| `control/inner_loop/` | Интерфейс к realtime inner-loop (реализация — `05_avionics`). |
| `control/actuators/` | Команды актуаторам / распределённым поверхностям. |
| `fault_management/detection/` | Детекция отказов (сенсоры, актуаторы, compute). |
| `fault_management/isolation/` | Изоляция отказавшего канала. |
| `fault_management/reconfiguration/` | Graceful degradation / reconfiguration. |
| `models/onnx/` | Локальные ONNX-веса (единственный runtime-путь в полёте). |
| `models/torchscript/` | Опциональный offline/dev экспорт. |
| `models/configs/` | Конфиги инференса (input size, thresholds, device). |
| `ros2/` | ROS 2 пакеты/ноды автономии. |

## `00_docs/`

| Подпапка | Назначение |
|----------|------------|
| `architecture/` | Системная и autonomy-архитектура. |
| `stack/` | Зафиксированный стек и зависимости. |
| `conventions/` | Именование, git, code style. |
| `adr/` | Architecture Decision Records. |
