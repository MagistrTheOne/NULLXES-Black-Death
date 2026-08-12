# MODE_ENVELOPES — CIVIL | DEFENSE

**Status:** Canon · 2026-08-13  
**ADR:** [ADR-008](../adr/ADR-008_DUAL_ENVELOPE.md)  
**Gate:** [MISSION_POLICY_SPEC.md](MISSION_POLICY_SPEC.md)

Один борт, один L0, два **MissionProfile envelope**. Переключатель на GSC. Boot = **CIVIL**.

```text
operator ──► /bd/mission/envelope_switch
                 │  operator_ack required for DEFENSE
                 ▼
         EnvelopeController
                 │
                 ├── CIVIL  → mission_profiles/<id>.yaml
                 └── DEFENSE → mission_profiles/defense/<id>.yaml
                 │
                 ▼
         /bd/mission/envelope + /bd/mission/profile
                 │
        DMI agent reloads gate ──► GoalMsg (same IntentKind)
                 │
                 ▼
              Guidance → L0   (weapon-blind, swarm-blind)
```

## Норматив 2026 (зафиксировано в контракте, не «сертификат в git»)

### РФ (гражданский контур)

| Норма | Что берём в код |
|-------|-----------------|
| ВЗК ст. 33 / учёт БВС 0.15–30 кг, регистрация >30 кг | `registration_class: uchet \| registraciya` |
| ПП РФ №1701 (30.11.2024) | связь/навигация/наблюдение; **удалённая идентификация** (индекс, категория, высота, координаты); **экстренное прекращение полёта** (посадка / RTL / безопасное приземление) |
| ЭРА-ГЛОНАСС / ПП 02.02.2026 №83, старт **01.03.2026** | RID payload `dest=era_glonass` ≥1 Гц при CIVIL. Не GOST-сертифицированный стек — хук |
| Приказ Росавиации №829-П | внешний контур устройства RID; мы отдаём поля, не подменяем тип |

### Международка (гражданский / dual-use)

| Норма | Что берём |
|-------|-----------|
| ICAO Model UAS / RPAS Panel SARPs 2026 | Remote ID, C2, DAA, UTM — интерфейсы, не второй автопилот |
| EU 2019/945+947, EN 4709-002 Remote ID | тот же RID-контракт |
| Dual-use / экспорт | национальный контроль. **Не** второй L0 и **не** наступательный РЭБ в репозитории |

DEFENSE не отменяет CIVIL-сертификацию борта: это **операционный envelope** + GSC COP. Публичный RID в DEFENSE может быть `rid_broadcast: false` (hold), не джеммер.

## Что такое 30–50 км

**Не CERBER.** Рабочая EO-дальность камеры — метры/десятки метров (pinhole + imgsz 640).  
**Да:** GSC `TerritorialCop.radius_m` 30 000 (`airspace.guard.v1`) или 50 000 (`isr.territory.v1`). Источники: Remote ID, ЭРА-ГЛОНАСС, ADS-B-like, operator, own_swarm.

Affiliation: `friend` = наш `agent_id` / SwarmHealth. Иначе `unknown`. Класса FOE нет.

## РЭБ в этом репозитории

Own-ship `/bd/gnss/integrity`: `ok` | `jam_loss` | `spoof_jump` | `hdop_high` | `stale`.  
Нет эмиттера, нет waveform, нет cookbook постановки помех.

## Профили

| Envelope | YAML | COP | RID | Airframe geofence |
|----------|------|-----|-----|-------------------|
| CIVIL | `inspection.powerline.v1` | 5 km | broadcast required | ±5 km, AGL 120 |
| CIVIL | `perimeter.alert.v1` | 5 km | broadcast required | ±2 km, AGL 150 |
| DEFENSE | `defense/airspace.guard.v1` | **30 km** | hold | ±8 km |
| DEFENSE | `defense/isr.territory.v1` | **50 km** | hold | ±20 km |

CHASE запрещён в **обоих**. NEVER_ACTIONS (WEAPON, JAM, FIRE_CONTROL, GUIDANCE_INTENT, …) запрещены в коде, YAML не может их включить.

## SoftBus

| Topic | Кто |
|-------|-----|
| `/bd/mission/envelope_switch` | operator → GSC |
| `/bd/mission/envelope` | EnvelopeSoftNode |
| `/bd/gsc/territorial_ingest` | GSC feeds |
| `/bd/gsc/territorial_track` | COP out |
| `/bd/gnss/integrity` | onboard monitor |
| `/bd/rid/broadcast` | onboard CIVIL |

## Код

- `dmi/envelope.py` — switch  
- `dmi/mission_policy.py` — gate + NEVER_ACTIONS  
- `dmi/territorial.py` — 30–50 km COP  
- `dmi/gnss_integrity.py` — own-ship  
- `dmi/rid_era.py` — ПП 1701 / ЭРА хук  
- `ros2/nodes/envelope_soft.py` · `rid_soft.py` · `gnss_integrity_soft.py`
