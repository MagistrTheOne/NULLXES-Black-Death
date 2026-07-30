# ALPHA 5×5 — Battery

**Pack usable density:** 180 Wh/kg  
**Chemistry:** Li-ion (semi-solid allowed later)  
**BMS:** dual-feed to compute A/B

## Sizing from prelim aero (design estimate, not measured)

| Item | Value |
|------|-------|
| \(P_{elec,md}\) | 1160 W |
| \(E\) for PE-05 6 h | 6960 Wh → \(m=38.7\) kg — **rejects MTOW** |
| Alpha pack mass (rev A) | **16.0 kg** |
| Usable energy | \(16\times180=\) **2880 Wh** |
| Endurance @ \(V_{md}\) | \(2880/1160\approx\) **2.5 h** |
| Endurance @ 50 km/h (~1850 W) | **≈1.6 h** |
| Dash 100 km/h | minutes only |

**PE-05 (6 h):** out of Alpha scope ([ADR-001](../../00_docs/adr/ADR-001_ALPHA_ARCHITECTURE_DEMONSTRATOR.md)).  
Alpha energy health: **≥2.0 h @ \(V_{md}\)** with 16 kg pack (~2.5 h analytic). Product 6 h → Beta-Endurance.

## Electrical

| Item | Spec |
|------|------|
| Series | 12S |
| Capacity | ~65 Ah pack-level (order, match Wh) |
| SOC RTB | 25% |
| SOC land-now | 12% |
| Contactors | independent A/B logic supplies |

Mass group **energy = 16.0 kg** (battery+BMS+HV wiring).
