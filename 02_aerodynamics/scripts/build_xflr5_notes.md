# XFLR5 workflow — ALPHA 5×5 (no CLI automation)

## Input from repo

- Planform stations: `02_aerodynamics/geometry/planform_stations.csv`
- Outline: `planform_outline.csv`
- Airfoils: `airfoils/mh45.dat`, `mh61.dat` (real Selig only)
- Blended sections: run `scripts/blend_sections.py` (fails closed if invalid)

## Steps

1. File → New Project `ALPHA_5x5`
2. Direct foil design → import MH45, MH61
3. Wing → define trapezoid: span 5.0 m, root chord 5.0 m, tip 3.0 m, LE sweep 22.5°
4. Assign MH61 (or 15% stretch) root → blend mid → MH45 tip
5. Analysis → Type 2 (fixed speed) V=27.8 m/s, ρ=1.225
6. Export polar / T1–T2 results → replace DESIGN ESTIMATE numbers in `loads/ALPHA_5x5_PRELIM_AERO.md`

## Until XFLR5 run completes

`ALPHA_5x5_PRELIM_AERO.md` remains a **design estimate only**. Do not promote it to flight polar data.
