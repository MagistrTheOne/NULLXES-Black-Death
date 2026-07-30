# ALPHA_5x5_REQUIREMENTS — Prototype Alpha

**Проект:** NULLXES BLACK DEATH  
**Статус:** Baseline locked · **ROLE: System Architecture Demonstrator** ([ADR-001](../00_docs/adr/ADR-001_ALPHA_ARCHITECTURE_DEMONSTRATOR.md))  
**Дата:** 2026-07-29  
**Класс:** civil infrastructure · flying wing / BWB  
**Масштаб этапа:** Prototype Alpha 5×5 → после Flight-1: Beta-Endurance | Beta-Heavy (см. `00_docs/PRODUCT_LINES.md`)

**Alpha не доказывает** endurance 6 ч / дальность 300 км / оптимальную аэродинамику финальной машины.  
**Alpha доказывает** целостную автономную архитектуру (L0, dual-compute, FM, guidance, CV, HIL, twin).

Изменение параметров §1 и замороженного списка ADR-001 — только новым ADR. Уточнения после Flight-1 — через `ALPHA_LESSONS_LEARNED` → ADR-021.

---

## 1. Locked baseline

| Параметр | Значение | Примечание |
|----------|----------|------------|
| Размах \(b\) | **5,0 м** | — |
| Площадь крыла \(S\) (цель) | **20 м²** | \(c_{\mathrm{mean}} = S/b = 4,0\) м |
| Aspect ratio \(AR = b^2/S\) | **1,25** | компактный BWB «5×5»; не классический high-AR |
| MTOW | **42 кг** | — |
| Payload | **10 кг** | ≈24 % MTOW |
| Endurance с payload | **≥2,0 ч @ \(V_{md}\)** (energy health) | **не** product 6 ч — см. PE-05 / ADR-001 |
| Крейсерская скорость | **90–110 км/ч** | dash envelope; endurance flight @ \(V_{md}\) |
| Дальность | **вне scope Alpha** | цель Beta-Endurance |
| Тяга | **2× основных** + опционально **2× VTOL-assist** | электрические |
| Энергия (этап 1) | **электрическая** (Li-ion / полутвёрдый) | hybrid — позже |
| Сенсоры | **4× камера** + **2× IMU** + **GNSS** + **1× лёгкий LiDAR** | onboard only |
| Compute | **2 канала A/B** | L0: C++17/20 · L1–L5: Python 3.11 |

---

## 2. Mission envelope (civil only)

Допустимые классы миссий (см. `missions/MISSIONS.md`):

1. Logistics  
2. Energy & Grid (support / inspection)  
3. Disaster Response  
4. Construction Support  
5. Transportation (cargo / limited pax per safety rules)  
6. Infrastructure inspection & support  

**Запрещено:** вооружение, боевые сценарии, военное применение — в требованиях, коде, симах, именовании режимов.

---

## 3. Derived flight targets (preliminary)

| Величина | Оценка | Формула / база |
|----------|--------|----------------|
| Wing loading \(W/S\) | **20,6 Н/м²** ≈ **2,1 кг/м²** | \(mg/S\), \(m=42\) кг |
| Cruise TAS | **25–30,6 м/с** | 90–110 км/ч |
| Nominal cruise | **27,8 м/с** | 100 км/ч |
| Требуемая энергия | см. `02_aerodynamics/loads/ALPHA_5x5_PRELIM_AERO.md` + battery doc | derived from \(P_{elec}\) |
| Полезная нагрузка | **10 кг** в грузовом отсеке / точках крепления | — |

Уточнение \(C_L\), \(C_D\), потребной тяги — после `02_aerodynamics` preliminary aero.

---

## 4. Propulsion & energy

| ID | Требование |
|----|------------|
| PE-01 | 2 независимых основных тяговых модуля (pusher или embedded — выбор в `04_propulsion_energy`). |
| PE-02 | Опционально 2× VTOL-assist; отказ VTOL не блокирует CTOL-режим. |
| PE-03 | Отказ 1 основного модуля → продолжение полёта в degraded mode (урезанный конверт). |
| PE-04 | Энергосистема электрическая; BMS + dual-feed к compute A/B. |
| PE-05 | Alpha energy health: **≥2,0 ч @ \(V_{md}\)** with 10 кг payload. **6 ч / 300 км — out of Alpha scope** (Beta-Endurance). |

---

## 5. Avionics & compute

| ID | Требование |
|----|------------|
| AV-01 | Два независимых compute-канала **A** и **B** (питание, хранилище, inference). |
| AV-02 | L0 (inner-loop, drivers, buses) — **C++17/20**; hard realtime. |
| AV-02b | Alpha languages: **Python 3.11 + C++ only** (Rust не используем). |
| AV-03 | L1–L5 autonomy — Python 3.11 + ROS 2 Jazzy+; полностью onboard. |
| AV-04 | Нет внешних API / облачных LLM / cloud inference в полёте. |
| AV-05 | Failover A↔B через fault management; L0 живёт при смерти high-level. |
| AV-06 | Синхронизация времени между каналами (см. `05_avionics/timing`). |

---

## 6. Sensors

| ID | Состав | Роль |
|----|--------|------|
| SEN-01 | 4× global shutter **1280×720@30**, FOV **90°** fwd/down, **110°** left/right | vision, YOLO/ONNX |
| SEN-02 | 2× IMU (ICM-42688 class), разнос **≥0,4 м** | fusion, redundancy |
| SEN-03 | 1× multi-band GNSS + mag | абсолютная навигация |
| SEN-04 | 1× mid-360 LiDAR, range **≥40 м**, **≥10 Hz** | препятствия / высота / mapping |

Потеря одного сенсорного канала → fusion с повышенной ковариацией + сужение конверта (см. autonomy FM).

---

## 7. Autonomy (summary)

| ID | Требование |
|----|------------|
| AU-01 | Слои L1–L5 по `00_docs/architecture/AUTONOMY_ARCHITECTURE.md`. |
| AU-02 | Inference: ONNX Runtime (+ GPU EP при наличии). |
| AU-03 | Decision: `AlphaBT` mode policy with degraded / RTB / SAFE_LOITER branches. |
| AU-04 | Dual-compute: primary/secondary; зеркало state; hot/warm standby. |
| AU-05 | Модели только в `06_autonomy/models/onnx/`. |

Детали: `06_autonomy/DUAL_COMPUTE.md`.

---

## 8. Structure & materials (Alpha intent)

| ID | Требование |
|----|------------|
| ST-01 | Силовая схема под MTOW 42 кг; load factors: `constraints/ALPHA_5x5_LOADS.md`. |
| ST-02 | Базовый материал: CFRP + пенопласт / Nomex (выбор в `03_structure`). |
| ST-03 | Обязателен aeroelasticity screening (flutter / divergence) уже на 5 м. |
| ST-04 | Mass breakdown: `03_structure/ALPHA_5x5_MASS_BREAKDOWN.md`. |

---

## 9. Aerodynamics (Alpha intent)

| ID | Требование |
|----|------------|
| AE-01 | Planform и геометрия: `02_aerodynamics/geometry/`. |
| AE-02 | Целевая \(S = 20\) м², \(b = 5\) м; LE sweep ориентир **20–25°**. |
| AE-03 | Профиль: низкий Re, высокий \(C_L/C_D\) — выбор отдельным файлом. |
| AE-04 | Preliminary aero + CFD path: XFOIL/XFLR5 → OpenFOAM/SU2. |

---

## 10. Safety & degraded modes (civil)

| Mode | Условие | Поведение |
|------|---------|-----------|
| NOMINAL | Все каналы OK | Полная миссия |
| DEGRADED_PROP | 1 main thruster lost | Урезанный конверт, завершение миссии / RTB |
| DEGRADED_SENS | Потеря камеры/IMU/LiDAR | Fusion degrade, осторожный план |
| DEGRADED_COMPUTE | Канал A или B lost | Failover; при необходимости упрощённый BT |
| SAFE_LOITER | Критический FM | Civil loiter / controlled landing site |
| RTB | Mission abort | Return to base / safe landing |

Пороги: `01_requirements/safety/ALPHA_5x5_FM_THRESHOLDS.md`.

---

## 11. Acceptance — Prototype Alpha (architecture demonstrator)

### Frozen configuration (LOCK)

Размеры · AR · mass rev A · battery 16 кг · sensors · stack · dual-compute · topics/interfaces · electric PDB intent — **LOCKED** per ADR-001 until Flight-1 + lessons learned.

### System gates

- [x] Геометрия planform \(S=20\) м² locked  
- [x] Mass breakdown rev A = 42 кг MTOW (design budget)  
- [x] Dual-compute A/B + FM + guidance/EKF algorithms (contracts)  
- [ ] Vision flight path: real ONNX + sha256 + camera drivers  
- [x] Preliminary aero analytic (design estimate only; XFOIL/XFLR5 pending)  
- [ ] Digital twin / Gazebo: real vehicle model + topic bridges  
- [ ] Build L0 (CMake library) + HIL failover on bench  
- [ ] **Flight-1** CTOL: hold mode · compute failover · degraded/RTB · complete without cloud / without required autonomy-loop pilot  

### Explicitly not Alpha acceptance

- 6 h endurance  
- 300 km range  
- AR optimization for product L/D  

---

## 12. Locked engineering defaults

| Параметр | Значение |
|----------|----------|
| Load factors | \(n_{+}=+3{,}8\), \(n_{-}=-1{,}5\); gust \(U_{de}=15\) м/с |
| \(V_{dive}\) | 154 км/ч |
| CTOL ground roll | ≤ 80 м; VTOL-assist **OFF** on flight-1 |
| Motors | 2× brushless pusher, **12S**, continuous **≥1,2 кВт** each; static thrust sum **≥0,55·MTOW** (≥226 Н) |
| Propellers | 2× **15–17″** (final pick after power model) |
| Battery mass | **16,0 кг** locked (rev A); Wh health-check only |
| Pack usable density | **180 Wh/kg** |
| Cameras | 4× GS 1280×720@30; FOV 90°/90°/110°/110° |
| IMU | 2× ICM-42688 class, ≥0,4 м apart |
| GNSS | 1× multi-band + mag |
| LiDAR | mid-360, ≥40 м, ≥10 Hz |
| Heartbeat / failover | 150 ms / ≤500 ms |
| Languages | Python 3.11 + C++17/20 only |

Details: `constraints/ALPHA_5x5_LOADS.md`, `interfaces/ALPHA_5x5_ROS_TOPICS.md`, `04_propulsion_energy/`.

---

## 13. Scale roadmap

| Этап | Роль | Статус |
|------|------|--------|
| **Alpha 5×5** | System Architecture Demonstrator | **LOCKED** (ADR-001) |
| **Beta-Endurance** | max time / range (new geometry) | after Flight-1 + ADR-021 |
| **Beta-Heavy** | volume / payload / infra ops | after Flight-1 + ADR-021 |
| Full platform ~50×50 | product composition | later |

Shared across all lines: autonomy canon, dual-compute, L0 boundary, civil-only, onboard-only.  
See `00_docs/PRODUCT_LINES.md`.

