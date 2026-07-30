# Как писать код по стеку BLACK DEATH

**Языки:** Python 3.11 (L1–L5, скрипты, симы) + C++17/20 (L0).  
**Правило:** новый код сразу в правильную папку. Без облачных API.

---

## 1. Карта: что куда писать

| Задача | Папка | Язык |
|--------|-------|------|
| CV / YOLO / камеры | `06_autonomy/perception/vision/` | Python |
| Сенсоры → ROS | `06_autonomy/perception/sensors/` | Python |
| EKF/UKF fusion | `06_autonomy/perception/fusion/` | Python |
| SLAM (нода) | `06_autonomy/perception/slam/` | Python/C++ wrapper |
| BT / миссии | `06_autonomy/planning/` | Python |
| Guidance setpoints | `06_autonomy/control/guidance/` | Python |
| Dual-compute | `06_autonomy/core/dual_compute/` | Python |
| Fault management | `06_autonomy/fault_management/` | Python |
| Inner-loop / PID / actuators | `05_avionics/flight_software/` | **C++** |
| Драйверы IMU/ESC/bus | `05_avionics/drivers/` | **C++** |
| Gazebo/AirSim сценарии | `07_simulation/` | Python + SDF/YAML |
| Aero скрипты | `02_aerodynamics/scripts/` | Python |
| FEA скрипты | `03_structure/scripts/` | Python |
| CI / lint | `99_tools/` | Python / shell |

---

## 2. CV / Vision — как писать самому

### Пайплайн (канон)

```
camera frame
   → OpenCV preprocess (resize, undistort, color)
   → ONNX Runtime YOLO (не Ultralytics в полёте)
   → postprocess (NMS уже в модели или свой)
   → ROS 2 publish detections
   → planning / FM читают
```

### Правила

1. **Полётный inference = ONNX Runtime.** Ultralytics/`torch` — только offline train/export.  
2. Веса класть в `06_autonomy/models/onnx/`, конфиг — `models/configs/`.  
3. Один модуль = один файл ответственности: `capture.py`, `preprocess.py`, `infer_yolo.py`, `vision_node.py`.  
4. Никаких `requests` к интернету в vision-коде.  
5. Камера упала → FM flag, не exception наружу без health.

### Offline: обучил → в самолёт

```text
# training machine (не flight image)
yolo export model=best.pt format=onnx opset=17
# copy → 06_autonomy/models/onnx/detector_vN.onnx
# config → 06_autonomy/models/configs/detector_vN.yaml
```

### Минимальный каркас

Смотри рабочие файлы:

- `06_autonomy/perception/vision/preprocess.py`
- `06_autonomy/perception/vision/infer_yolo.py`
- `06_autonomy/perception/vision/vision_node.py`
- `06_autonomy/models/configs/detector_alpha.yaml`

Паттерн: класс без ROS внутри → тонкая ROS-нода снаружи (легко тестировать).

### Зависимости CV

См. `06_autonomy/requirements-autonomy.txt` + `00_docs/stack/AUTONOMY_LIBS.md`.

---

## 3. Planning / behaviour

- Миссии: `planning/missions/` — данные (YAML), не хардкод в BT.  
- Логика: `planning/behaviour/` — `AlphaBT` mode policy (Alpha).  
- Каждая degraded-ветка (пропали камера / канал A / тяга) — **явный** leaf/subtree.  
- Траектории: чистые функции `(state, goal) → trajectory`; нода только публикует.

---

## 4. Dual-compute

Писать в `core/dual_compute/`. Уже есть:

- `heartbeat.py` — peer alive  
- `state_mirror.py` — пакет зеркала  
- `active_election.py` — кто active  

Не дублировать election в vision/planning — только читать `active` / публиковать health.

---

## 5. C++ L0 — как писать

| Делать | Не делать |
|--------|-----------|
| Детерминированный цикл (фиксированный dt) | Python внутри hard loop |
| Принимать setpoints из ROS 2 / shared memory | Тяжелый CV в L0 |
| Watchdog: нет setpoint → hold / contingency | Блокирующие alloc в hot path |
| Код в `05_avionics/flight_software/` | Логика миссий в C++ |

Скелет цикла (концепт):

```cpp
// 05_avionics/flight_software/ — pseudocode pattern
while (running) {
  auto sp = setpoint_buffer.latest();   // from autonomy
  auto imu = imu_driver.read();
  auto cmd = inner_loop.step(sp, imu, dt);
  actuator_bus.write(cmd);
  sleep_until(next_tick);
}
```

Сборка: CMake + colcon (`99_tools/colcon/`). Alpha: C++17 минимум, C++20 ок.

---

## 6. Симуляция — как писать

| Что | Где | Как |
|-----|-----|-----|
| Сценарии миссий | `07_simulation/scenarios/` | YAML: старт, ветер, отказы |
| Gazebo модели/world | `07_simulation/gazebo/` | SDF + ROS 2 bridge (WSL2) |
| AirSim | `07_simulation/airsim/` | settings.json + Python client |
| Digital twin topic map | `07_simulation/digital_twin/topic_map.yaml` | те же имена, что на железе; runtime twin **BLOCKED** |
| HIL failover | `07_simulation/hil/` | убиваем канал A, ждём takeover |

**Правило:** autonomy-код не знает, sim это или борт. Только ROS API / драйверный адаптер.

Порядок работы симы:

1. Поднять Gazebo/AirSim  
2. Запустить dual_compute A/B (оба процесса)  
3. Запустить vision на sim-камерах  
4. Гонять сценарии из `scenarios/`  
5. Те же сценарии → `10_tests/`

---

## 7. Aero / structure scripts

- Геометрия: `02_aerodynamics/geometry/generate_planform.py`  
- Профили: `02_aerodynamics/airfoils/fetch_airfoils.py`  
- Потом: `scripts/` для XFOIL batch / парсинга polars  
- FEA: вход из geometry + `03_structure/load_paths/`  

Не класть одноразовые ноутбуки в корень — только в соответствующий `scripts/` или `00_docs/` если это отчёт.

---

## 8. Стиль (жёстко)

- Python: 3.11, type hints на публичных функциях, без cloud SDK.  
- Конфиги: YAML рядом с модулем или в `models/configs/`.  
- Тесты: `10_tests/unit/...` зеркалят путь модуля.  
- Имена civil-only.  
- Коммиты — по запросу; секреты не в git.

---

## 9. Чеклист «новый vision-модуль»

1. Код в `perception/vision/`  
2. ONNX путь только из config  
3. Unit-тест на preprocess + decode (synthetic tensor for algorithm only; no fake cameras)  
4. Node publishes detections + health; **BLOCKED** without real ONNX + camera driver  
5. HIL only with real I/O or certified sim plugins — no invented sensor streams  

---

## 10. Ссылки канона

- Стек: `STACK.md`  
- Libs: `AUTONOMY_LIBS.md`  
- Архитектура ИИ: `../architecture/AUTONOMY_ARCHITECTURE.md`  
- Dual-compute: `../../06_autonomy/DUAL_COMPUTE.md`  
- Alpha requirements: `../../01_requirements/ALPHA_5x5_REQUIREMENTS.md`
