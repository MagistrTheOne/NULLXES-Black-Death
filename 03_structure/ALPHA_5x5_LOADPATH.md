# ALPHA 5×5 — силовая схема (рамы / лонжероны / сэндвич)

**Status:** structural concept v0  
**MTOW:** 42 кг · materials intent: **CFRP + foam/Nomex core**  
**Mass budget structure:** 14 кг (`ALPHA_5x5_MASS_BREAKDOWN.md`)

## 1. Выбранная схема

**Двухлонжеронный box + нервюры (рамы) + sandwich skin.**

| Элемент | Решение | Зачем |
|---------|---------|--------|
| Front spar | ~**25 %** локальной хорды, C/box CFRP | изгиб + крепление LG/hardpoints |
| Rear spar | ~**65 %** хорды, C/box CFRP | кручение + hinge элевонов |
| Ribs / рамы | на станциях y = 0, 0.625, 1.25, 1.875, 2.5 м + промежуточные | форма профиля, локальная жёсткость |
| Carry-through | центр (y≈±0,4 м) — непрерывный box | BWB: нет классического фюзеляжа |
| Skin | CFRP sandwich, core foam (крыло) / Nomex (центр, где объём/удар) | вес vs жёсткость |
| Hardpoints | payload bay floor + LG attachments на front spar | 10 кг payload |

**Почему не mono-spar / только foam:**
- низкий AR + большой объём → кручение критично → нужен **closed box** (два лонжерона + skin)
- элевоны требуют задний силовый пояс
- dual-compute / battery — точечные массы → рамы разносят нагрузки

## 2. Рамы (нервюры) — правило

На каждой станции из `geometry/planform_stations.csv`:

1. Контур = локальный профиль (MH61/MH45 blend) × chord  
2. Вырезы под лонжероны (front/rear)  
3. Облегчение (lightening holes) где FEA позволит  
4. Root ribs (y=0…0,4): усиленные — payload + battery bulkhead  

Доп. рамы между станциями, если шаг > ~0,4 м по чувствительности к skin buckling (FEA).

## 3. Материалы (Alpha BOM intent)

| Зона | Материал |
|------|----------|
| Spar caps | unidirectional CFRP |
| Spar webs / ribs | CFRP biax / foam sandwich |
| Outer skin | CFRP twill/biax + foam core |
| Center body panels | CFRP + Nomex (где нужна ударостойкость пола) |
| Bonding | structural epoxy (aerospace-grade civil) |

## 4. Load path (кратко)

```
Aero pressure → skin → ribs → spars → carry-through → LG / hardpoints
Elevon hinge loads → rear spar → ribs → box
Landing → LG → front spar / local frames → carry-through
Payload 10 kg → floor frames → spars
Battery → center bulkheads → spars
```

## 5. Aeroelasticity (обязательно на 5 м)

- Flutter / divergence screening до первого полёта  
- Инструменты: Doublet Lattice / CalculiX modal + unsteady (или Code_Aster)  
- Цель: margin по flutter speed > Vdive (Vdive TBD после envelope)

## 6. Next

1. FEA mesh от geometry + airfoil contours  
2. Load factors (TBD) → sizing spar caps  
3. Обновить mass breakdown после first sizing
