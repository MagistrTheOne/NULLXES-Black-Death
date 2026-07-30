# ALPHA 5×5 — Draft planform geometry

**Status:** draft v0 · locked to baseline \(b=5\) м, \(S=20\) м²  
**Source:** `01_requirements/ALPHA_5x5_REQUIREMENTS.md`  
**Note:** root chord берётся из \(S\) и footprint «5×5», не из чернового 2,2–2,4 м (тот дал бы \(S\approx7\) м²).

## 1. Global

| Параметр | Символ | Значение |
|----------|--------|----------|
| Span | \(b\) | 5,000 m |
| Half-span | \(b/2\) | 2,500 m |
| Reference area | \(S\) | 20,00 m² |
| Mean geometric chord | \(\bar{c}=S/b\) | 4,000 m |
| Aspect ratio | \(AR=b^2/S\) | 1,25 |
| Centerline (root) chord | \(c_r\) | **5,000 m** |
| Tip chord | \(c_t\) | **3,000 m** |
| Taper ratio | \(\lambda=c_t/c_r\) | 0,60 |
| LE sweep (constant) | \(\Lambda_{LE}\) | **22,5°** |
| TE sweep (derived) | \(\Lambda_{TE}\) | ≈ **−21,1°** (`generate_planform.py`) |
| MAC (approx. trap.) | \(c_{MAC}\) | ≈ 4,082 m |
| \(y_{MAC}\) from CL | — | ≈ 1,146 m |
| Design Re (cruise, MAC) | \(Re=\frac{V c}{\nu}\) | ~7,4e6 @ 28 м/с, ISA SL (порядок) |

Проверка площади трапеции: \(S=(c_r+c_t)/2\cdot b=(5+3)/2\cdot5=20\) м² — OK.

## 2. Coordinate system

- Origin: nose / LE on centerline  
- \(+x\): aft (chordwise)  
- \(+y\): right wing  
- \(+z\): up  

## 3. Planform outline (plan view, z=0)

Станции и XYZ: `planform_stations.csv`  
Генератор: `generate_planform.py`

Ключевые точки (м):

| Point | x | y |
|-------|---|---|
| Nose (LE CL) | 0,000 | 0,000 |
| TE CL | 5,000 | 0,000 |
| LE tip R | \(2{,}5\cdot\tan(22{,}5°)\) ≈ 1,035 | 2,500 |
| TE tip R | LE tip + \(c_t\) ≈ 4,035 | 2,500 |

Зеркало по \(y\) для левой половины.

## 4. Sections (draft)

| Station \(y\) (m) | Chord (m) | LE x (m) |
|-------------------|-----------|----------|
| 0,00 | 5,000 | 0,000 |
| 0,625 | 4,500 | 0,259 |
| 1,250 | 4,000 | 0,518 |
| 1,875 | 3,500 | 0,776 |
| 2,500 | 3,000 | 1,035 |

Линейный taper + constant LE sweep.

## 5. Airfoil (locked draft)

- **MH61** (root, t/c→15 % при необходимости) → blend → **MH45** (tip)  
- Канон: `02_aerodynamics/airfoils/ALPHA_5x5_AIRFOIL_SELECTION.md` 

## 6. Files

| File | Role |
|------|------|
| `PLANFORM.md` | этот документ |
| `planform_stations.csv` | станции LE/TE |
| `planform_outline.csv` | замкнутый контур (для CAD/CFD) |
| `generate_planform.py` | пересчёт при смене sweep/taper |
