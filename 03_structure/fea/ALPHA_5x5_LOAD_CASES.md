# ALPHA 5×5 — FEA load cases

**Loads:** `01_requirements/constraints/ALPHA_5x5_LOADS.md`  
**MTOW:** 42 kg · \(W=411.8\) N

| ID | Case | Load | Notes |
|----|------|------|-------|
| LC1 | Maneuver \(n_{+}\) | \(+3.8\,W\) distributed aero (elliptic approx) | spar cap tension/compression |
| LC2 | Maneuver \(n_{-}\) | \(-1.5\,W\) | |
| LC3 | Gust | \(U_{de}=15\) m/s incremental at \(V_c=100\) km/h | screening |
| LC4 | Landing | 2.0 g vertical at LG points on front spar | CTOL |
| LC5 | Elevon hinge | hinge moment from \(C_h=0.01\) @ \(q(V_{dive})\) on elevon area | rear spar |
| LC6 | Single motor torque | max continuous torque on one pusher mount | local frames |

Inertia relief: include battery 16 kg center + payload 10 kg bay + motors at tip-aft mounts.
