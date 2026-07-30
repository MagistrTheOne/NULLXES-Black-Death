# ALPHA 5×5 — Flutter / divergence screening

**Status:** method + interim checklist — **not** a completed FEA/DLM flutter clearance.  
**Requirement:** \(V_{flutter} > 1.15\,V_{dive}\) = **49.2 m/s** (177 km/h)  
**Refs:** Bisplinghoff & Ashley; Dowell; Doublet Lattice Method

## Method (Alpha)

1. **Modal FEA** (CalculiX): first bending + torsion of wing box from `03_structure` spar/rib layout; MTOW mass distribution incl. battery/payload.  
2. **Unsteady aero:** Doublet Lattice on planform stations (`geometry/planform_stations.csv`), Mach≈0, density ISA SL.  
3. **Match:** \(pk\) or \(k\)-method crossing — document \(V_f\) for modes 1–4.  
4. **Divergence:** static aeroelastic \(q_{div}\) from torsional stiffness vs aerodynamic moment slope.

## Interim analytic screen (order-of-magnitude)

For low-AR thick BWB, torsion frequency tends to be high relative to classic high-AR sailplanes, but **control-surface (elevon) flutter** is the Alpha risk.

| Check | Alpha action |
|-------|----------------|
| Elevon mass balance | hinge ahead of LE of surface; mass balance ≥90% |
| Freeplay | ≤0.1° elevon |
| Rear spar stiffness | rear spar @ 65%c continuous tip-to-tip through carry-through |
| Speed limit until FEA+DLM done | ops limit **\(V_{ne}=120\) km/h** (< \(V_{dive}\)) for early flights |

## Pass/fail

| Gate | Status |
|------|--------|
| Doc + ops \(V_{ne}\) | **PASS (interim)** |
| CalculiX + DLM numeric \(V_f\) | **OPEN** — run before expanding envelope to \(V_{dive}\) |

Output target: `03_structure/fea/` modal frequencies + this file updated with \(V_f\) table.
