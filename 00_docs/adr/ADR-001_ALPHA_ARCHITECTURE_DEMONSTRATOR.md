# ADR-001 — Alpha role: System Architecture Demonstrator

**Status:** Accepted  
**Date:** 2026-07-29  
**Deciders:** NULLXES systems architecture (project canon)

## Context

Preliminary aero at AR=1.25 showed PE-05 (6 h endurance) is physically incompatible with MTOW 42 kg. Mixing aero redesign (AR, MTOW, mission, energy) with unfinished Flight-1 would couple airframe and autonomy failures — root cause becomes unreadable.

## Decision

**Prototype Alpha 5×5 is a System Architecture Demonstrator only.**

It is **not**:
- an endurance demonstrator
- a range demonstrator
- an aerodynamics optimization vehicle for the 50×50 product

Alpha exists to prove one statement:

> The autonomous civil aviation platform architecture works as one integrated system under real faults and remains predictable.

## Locked until Flight-1 + ALPHA_LESSONS_LEARNED

Do **not** change without a new ADR that explicitly supersedes this one:

- geometry (b, S, AR, sweep, airfoils)
- MTOW / mass rev A
- battery mass 16 kg / energy architecture (electric)
- sensor suite
- stack (Python 3.11 + C++ + ROS 2)
- dual-compute A/B
- ROS topics / interfaces
- PDB / wiring topology intent

Aero/CFD/XFLR5 work on Alpha is **supportive** (loads, flutter screen, sim fidelity) — not a license to reshape the planform for endurance.

## Alpha acceptance (engineering)

Flight-1 / program success means the vehicle can, without cloud APIs:

1. CTOL takeoff (civil)
2. Hold guided mode
3. Survive single compute loss (failover ≤500 ms)
4. Enter correct degraded / SAFE_LOITER / RTB behaviour
5. Complete flight without required pilot intervention in the autonomy loop

Endurance target for Alpha: **≥2.0 h @ \(V_{md}\)** as *energy health check*, not product claim. **6 h / 300 km are out of Alpha scope.**

## After Flight-1

1. Write `00_docs/adr/ALPHA_LESSONS_LEARNED.md` (or `00_docs/ALPHA_LESSONS_LEARNED.md`)
2. Only then open **ADR-021 — Start Beta Geometry**
3. Fork product lines (architecture stays shared):

```
BLACK DEATH
    Alpha 5×5  →  Architecture Verified
         ├─ Beta-Endurance   (AR, span, batteries, speed)
         └─ Beta-Heavy       (volume, payload, infrastructure ops)
```

## Consequences

- PE-05 rewritten for Alpha (see requirements).
- No AR/MTOW/mission-energy churn before Flight-1.
- Autonomy, L0, HIL, twin remain the critical path.
- Visual/product 50×50 and long endurance belong to Beta branches.

## Rejected alternatives (for now)

| Alternative | Why rejected pre-Flight-1 |
|-------------|---------------------------|
| Rewrite Alpha AR for 6 h | Couples brain + body debug |
| Hybrid on Alpha | Scope explosion |
| Raise MTOW to chase Wh | Still weak without AR; pollutes baseline |
| “Alpha = mini 50×50 + endurance” | Two goals, zero clean proof |
