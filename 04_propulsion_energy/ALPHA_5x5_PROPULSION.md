# ALPHA 5×5 — Propulsion

**Flight-1:** CTOL only · VTOL-assist **OFF**  
**Ref power:** `02_aerodynamics/loads/ALPHA_5x5_PRELIM_AERO.md` (**design estimate** until XFOIL/XFLR5 + static thrust bench)

## Configuration

| Item | Spec |
|------|------|
| Layout | 2× independent brushless **pusher** |
| Bus | **12S** Li-ion (nominal ~44.4 V) |
| Continuous power | **≥1.2 kW each** (floor); dash/climb headroom preferred |
| Static thrust (sum) | **≥226 N** (0.55·MTOW) |
| Propellers | 2× **15–17″** folding or fixed (pick after static thrust bench) |
| ESC | 2× ≥60 A continuous, separate feeds |
| Single-motor fail | DEGRADED_PROP — remaining motor + elevons for RTB |

## Mission power use

| Mode | Speed | \(P_{elec}\) (est. analytic) | Notes |
|------|-------|---------------------|-------|
| Endurance / loiter | ~29 km/h (\(V_{md}\)) | ~1160 W | primary energy mode |
| Dash | 100 km/h | ~12.7 kW | short; not for 6 h |
| Climb / takeoff | — | use static thrust budget | CTOL ≤80 m |

## Mass (propulsion group)

**4.0 kg** total: motors + props + ESC + mounts (rev A; was 4.5).

## Files

- Energy: `energy_storage/ALPHA_5x5_BATTERY.md`
- PDB: `power_distribution/ALPHA_5x5_PDB.md`
- Thermal: `thermal/ALPHA_5x5_THERMAL.md`
