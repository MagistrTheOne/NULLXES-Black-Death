# Системная архитектура — обзор

## Машина

- Тип: flying wing / blended wing body (civil infrastructure drone/platform)
- Масштаб: ~50×50 м
- Роли: logistics · energy & grid · disaster response · construction · transportation · infrastructure
- Управление: полностью автономное onboard; распределённые каналы; graceful degradation

## Домены

```
01_requirements  →  задаёт миссии и ограничения
        ↓
02_aerodynamics  +  03_structure  +  04_propulsion_energy
        ↓  модель платформы / нагрузки / энергия
05_avionics (L0 realtime)  ↔  06_autonomy (L1–L5)
        ↓
07_simulation / 10_tests  → верификация
08_prototypes / 09_manufacturing → воплощение
```

## Избыточность (платформа)

- Распределённая силовая и энергетическая схема (объём BWB)
- Многоканальная авионика и compute
- Autonomy FM: detect → isolate → reconfigure
- Inner-loop живёт без high-level AI

Детали ИИ: [`AUTONOMY_ARCHITECTURE.md`](AUTONOMY_ARCHITECTURE.md). Поверхностная карта всей системы: [`ARCHITECTURE.md`](ARCHITECTURE.md).
