# ADR-002 — Distributed Mission Intelligence (DMI) v1

**Status:** Accepted  
**Date:** 2026-07-31  
**Deciders:** NULLXES systems architecture (project canon)  
**Refs:** [ADR-001](ADR-001_ALPHA_ARCHITECTURE_DEMONSTRATOR.md) · [DMI_V1](../architecture/DMI_V1.md)

## Context

Single-ship Alpha (Black Judgment) proves L0–L5 + dual-compute. Multi-platform civil missions (logistics, inspection, disaster) need coordinated task/sector assignment without putting a swarm inside the flight control loop, and without cloud/5G dependence for degraded flight.

Survey literature (swarm / MARL / consensus) mixes tactical flight with collective intelligence. That couples failures and violates production-first L0 isolation.

## Decision

Introduce **DMI v1** — Distributed Mission Intelligence (partner synonym: Collective Mission Intelligence / CMI):

1. **L6 Swarm Ops** sits **above** AlphaBT. It assigns intents/tasks/sectors and exchanges world facts.
2. **L0 is swarm-blind.** Inner-loop receives only guidance setpoints from the active compute channel. No DMI imports in `05_avionics`.
3. **Ground Swarm Coordinator** (optional when link OK) owns **Mission Score** allocation. Agents only `ACCEPT` / `REJECT` + status.
4. **SwarmIntent** is a mission goal (e.g. explore sector B7), not a stick command. Bridge → `GoalMsg` / mode hints only.
5. **Shared World Cache** — best-effort facts with TTL/confidence; not a global realtime map.
6. **Event-driven bus philosophy** — publish on significant change (intent, obstacle, mode, peer, task), not fixed high-rate spam for DMI/mirror-class traffic.
7. **Swarm Health:** ONLINE → LIMITED → LOST → RECOVERED; maps into FM peer/agent awareness.
8. Agents are **Black Judgment-class / practice airframes**, not N× BLACK DEATH 50×50.

### Explicitly out of DMI v1

Raft, Paxos, MARL onboard, cloud AI in the flight path, 5G as a hard dependency, neuromorphic compute, GPL drop-in of external swarm demos.

### PRACTICE stages (hardware)

| Stage | When | Platform | Proves |
|-------|------|----------|--------|
| 1 | ~2026-08-03 | edu sample airframe | bus, L0 hold, real IMU path, DMI intent on host |
| 2 | ~2026-09 | Skywalker X8 PNP (Flight-1) | same contracts on wing; CTOL practice. BOM: `FLIGHT1_BOM_LOCK.md` |

Alpha 5×5 geometry remains locked per ADR-001. Practice frames do **not** reopen Alpha planform.

## Consequences

- New package `06_autonomy/dmi/` + topics `/bd/dmi/*`.
- Topic map and twin YAML extended; digital twin may later host N agents on the same names.
- Unit tests cover DMI algorithms before hardware; practice bench tests stay BLOCKED without real drivers.
- Loss of ground coordinator → agents keep **last accepted intent** + local FM; no new sector assignment until link returns.
