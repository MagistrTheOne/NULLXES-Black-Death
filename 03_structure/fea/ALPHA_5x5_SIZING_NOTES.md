# ALPHA 5×5 — First structural sizing notes

**Status:** hand/beam DESIGN ESTIMATE — **not** CalculiX FEA results.  
**Method:** hand / beam on box spars · allowables from `materials/ALPHA_5x5_MATERIALS.md`  
**LC driver:** LC1 \(n=3.8\)

## Wing root bending (order)

Half weight × arm ≈ \((W/2)\times(b/4)=411.8/2\times1.25=257\) N·m at 1 g  
At 3.8 g: \(M_{root}\approx980\) N·m

Spar box height (root): \(h\approx0.15\times c_r=0.75\) m (thick BWB — use structural height **0.25 m** usable box)  
Cap force \(F\approx M/h=980/0.25=3920\) N  
UD area \(A=F/(\sigma_{allow}/1.5)=3920/(600e6/1.5)=9.8\times10^{-6}\) m² ≈ **10 mm²** per cap (very light — stiffness/flutter will size up)

## Stiffness-driven (Alpha lock)

| Member | Start size |
|--------|------------|
| Spar cap UD | **2 mm × 20 mm** each (upper/lower), front+rear |
| Spar web biax | **1.5 mm** |
| Skin sandwich | **0.6 mm** CFRP faces + **8 mm** foam (wing) |
| Root ribs | **2 mm** biax solid / sandwich |
| Center Nomex floor | **10 mm** core + 0.8 mm faces |

Mass check → structure group target **9.0 kg** after battery reallocation (rev A).

## Next FEA

Import `load_paths/spar_stations.csv` into CalculiX beam/shell model; validate tip deflection under LC1 < 5% half-span; update this file with eigenvalues for flutter screen.
