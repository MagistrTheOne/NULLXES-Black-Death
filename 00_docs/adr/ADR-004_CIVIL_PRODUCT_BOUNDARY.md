# ADR-004 — Civil Product Boundary

**Status:** Accepted  
**Date:** 2026-08-08  
**Deciders:** NULLXES systems architecture  
**Refs:** [CERBER.md](../architecture/CERBER.md) · [CERBER_DATASETS.md](../architecture/CERBER_DATASETS.md) · [ADR-002](ADR-002_DMI_V1.md)

## Context

CERBER / POSEIDON / DMI are dual-use capable as perception and coordination stacks. Product intent must stay civil: infrastructure, disaster, logistics, airspace awareness. Military kill-chain framing and munition interfaces must not enter code, datasets, or SoftBus contracts.

## Decision

1. **Intended purpose:** civil swarm intelligence — sense, track, alert, explore, loiter, RTB, escort/deny **presence**.
2. **Forbidden interfaces:** munition bus, fire-control lock, kill-score, targeting→weapon actuators.
3. **Forbidden datasets:** battle-tank / weapon / fire-control label sets (see CERBER_DATASETS REJECT).
4. **No-link degrade:** last accepted intent + SAFE_LOITER / RTB only; no new engage target without pre-authorized civil mode.
5. **L0 remains swarm-blind and weapon-blind.** Guidance outputs setpoints only.
6. **Human-on-loop** for mission mode changes when link is up; autonomy continues civil degrade when link is down.
7. **Runtime inference:** ONNX Runtime / TensorRT on NULLXES hardware and servers only. No cloud LLM / Ollama in the flight or mission decision path.

### Mission matrix

| Mission | Allowed | Forbidden |
|---------|---------|-----------|
| Airspace guard | Detect/track UAV → WorldFact → alert / escort / geo-deny presence | Kinetic munition |
| Infra inspect | human/vehicle/power_line/fire facts | Weapon DET packs |
| Disaster | explore sectors, LOITER, RTB | Strike tasking |
| Logistics | GOTO_XYZ, LOITER | Target lock for harm |

## Consequences

- ADR-005 POSEIDON packs inherit this boundary.
- CI should reject weapon/tank dataset paths in train packs.
- Product docs and SoftBus topic names stay civil-only.
