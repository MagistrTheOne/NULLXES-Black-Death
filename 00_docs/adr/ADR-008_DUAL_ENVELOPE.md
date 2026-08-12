# ADR-008 — Dual mission envelope (CIVIL | DEFENSE)

**Status:** Accepted  
**Date:** 2026-08-13  
**Deciders:** Maga / NULLXES systems  
**Refs:** [ADR-004](ADR-004_CIVIL_PRODUCT_BOUNDARY.md) · [ADR-007](ADR-007_BLACK_ATLAS.md) · [MODE_ENVELOPES.md](../architecture/MODE_ENVELOPES.md)

## Context

One airframe (BLACK DEATH / Alpha) must keep a civil product path (RF БАС 2026, ICAO/EU Remote ID) and, under operator authority, a defense *application* envelope: long-range territorial picture (30–50 km) via identification / GNSS / EW-*awareness*, not a second autopilot and not a weapon bus.

CERBER EO range is tens of metres, not tens of kilometres. 30–50 km is a GSC COP radius.

## Decision

1. **One L0.** Swarm-blind and weapon-blind in both envelopes. No `/bd/weapon/*`, no fire-control, no munition, no jammer/spoof emitter.
2. **Switch = MissionProfile + GSC envelope**, not a second stack. Boot **CIVIL**. DEFENSE requires `operator_ack` and a YAML whose `envelope: defense` matches.
3. **Same IntentKind verbs** (`GOTO_XYZ` / `LOITER` / `RTB` / `EXPLORE_SECTOR`). ATLAS still emits `AllocationPlan` only. DMI still owns TaskOffer / ACCEPT / REJECT.
4. **30–50 km** = `TerritorialCop` on GSC (`remote_id` | `era_glonass` | `adsb` | `operator` | `own_swarm`). Affiliation is `friend` (our `agent_id`) or `unknown`. FOE is not a detector class.
5. **РЭБ in this repo** = own-ship GNSS integrity (`jam_loss` / `spoof_jump` / `hdop_high`). Not an attack cookbook.
6. **CIVIL RF 2026 hooks:** Remote ID broadcast shaped for ЭРА-ГЛОНАСС (ПП №1701, учёт 0.15–30 кг / регистрация >30 кг). Interface payloads, not a certified GOST stack. CIVIL YAML cannot set `rid_broadcast: false`.
7. **NEVER_ACTIONS** are hardcoded. YAML cannot enable WEAPON / JAM / SPOOF / FIRE_CONTROL / GUIDANCE_INTENT.

## Consequences

- Profiles: `mission_profiles/*.yaml` (civil) and `mission_profiles/defense/*.yaml`.
- SoftBus: `/bd/mission/envelope`, `/bd/mission/envelope_switch`, `/bd/gsc/territorial_*`, `/bd/gnss/integrity`, `/bd/rid/broadcast`.
- ADR-004 remains the civil product boundary. DEFENSE does not reopen kill-chain interfaces.
