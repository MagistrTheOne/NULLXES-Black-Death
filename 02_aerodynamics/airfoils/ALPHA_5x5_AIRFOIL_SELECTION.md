# ALPHA 5×5 — Airfoil selection (locked draft)

**Status:** selected v0  
**Constraint:** tailless BWB → **reflex** обязателен  
**Re cruise (MAC):** ~7×10⁶ @ 28 м/с — не «микро-Re»; профиль не из парковых планеров 1e5.

## 1. Decision

| Station | y (m) | Family | t/c | Role |
|---------|-------|--------|-----|------|
| Root / centerbody | 0,00 – 1,00 | **MH61** (+ thickness stretch to **15 %** если нужен объём) | 12–15 % | объём payload/battery, Cm≥0 |
| Mid | 1,00 – 1,875 | blend MH61 → MH45 | — | гладкий переход |
| Tip | 1,875 – 2,50 | **MH45** | ≈9,8 % | Cl/Cd, элевоны |

**Почему MH, не NACA/Clark Y**

| Кандидат | Вердикт |
|----------|---------|
| **MH61 + MH45** | Заточены под tailless/plank; reflex; открытые координаты; XFOIL/XFLR5-friendly |
| HS / JW flying-wing | запасной ряд, если MH не сойдётся по Cm на полном 3D |
| NACA 4/5/6 digit | нет готового reflex → отказ для чистого flying wing |
| Толстый symmetric | объём есть, trim/ Cm плохой без стабилизатора |

## 2. Control surfaces (геометрия поверхностей)

- **Элевоны** на TE: от ≈40 % полуразмаха до tip (y≈1,0…2,5 м)
- Хорда элевона: **20 %** локальной хорды (старт)
- Split / crow — опция позже; Alpha CTOL: elevon + differential thrust

## 3. Файлы

| Path | Content |
|------|---------|
| `airfoil_selection.yaml` | machine-readable lock |
| `mh45.dat` / `mh61.dat` | Selig/UIUC format (скачать скриптом) |
| `fetch_airfoils.py` | тянет координаты в эту папку |
| `BLEND.md` | правило интерполяции по y |

## 4. Next aero steps

1. XFOIL: MH45 / MH61 @ Re=1e6…8e6, α-sweep, Cm check  
2. XFLR5: 3D VLM на `geometry/planform_*.csv` + эти профили  
3. Если Cm_total < 0 на cruise → увеличить reflex / twist (washout TBD)

## 5. Rejected for Alpha

- Один профиль на всё крыло (толстый root убивает tip или тонкий tip убивает объём)
- Не-reflex «потом докрутим стабилизатором» — стабилизатора нет
