# DMI World Ontology

**Status:** Canon v1 · 2026-08-08  
**Refs:** [ADR-002](../adr/ADR-002_DMI_V1.md) · [ADR-004](../adr/ADR-004_CIVIL_PRODUCT_BOUNDARY.md) · [DMI_V1.md](DMI_V1.md)  
**Palantir remap:** Ontology nouns/verbs → SoftBus objects/relations/actions — **no LLM agents in flight path**.

## Principle

```text
WorldFact     = observation snapshot (projection)
WorldObject   = persistent entity in mission world
Relation      = typed link between objects / agents
Event         = state transition or observation change
```

CERBER/POSEIDON do not feed DMI a “bbox 0.91”. They feed / update **WorldObjects** with pose, covariance, track, and provenance.

## WorldObject

| Field | Type | Notes |
|-------|------|-------|
| `object_id` | str | Stable id (often `trk-{track_id}` or UUID) |
| `type` | str | Civil taxonomy (below) |
| `x,y,z` | float | Position in `frame_id` |
| `vx,vy,vz` | float | Velocity (0 if unknown) |
| `cov_xx,cov_yy,cov_zz` | float | Position uncertainty |
| `frame_id` | str | Default `enu` |
| `source_id` | str | Sensor / agent id |
| `confidence` | float | [0,1] |
| `track_id` | int | `-1` if none |
| `state` | str | `observed` \| `tentative` \| `confirmed` \| `lost` \| `handoff` |
| `attrs` | dict[str,str] | Specialist attrs (e.g. `make`, `model`, `attr_unknown`) |
| `first_seen_s` | float | |
| `last_seen_s` | float | |
| `trace_id` | str | Links Flight Recorder |
| `stamp_ns` / `sensor_stamp_ns` | int | |

### Civil type taxonomy (ObservationInterest)

| type | Source lane |
|------|-------------|
| `human` | CERBER |
| `vehicle` | CERBER (+ VehicleAttr pack for make/model when low-AGL) |
| `uav` | CERBER / POSEIDON uav |
| `landing_zone` | CERBER |
| `obstacle` | CERBER / SceneSeg |
| `power_line` | CERBER / POSEIDON power |
| `road` / `building` / `forest` / `water` | CERBER / SceneSeg |
| `fire` | CERBER / POSEIDON fire |
| `infrastructure` | CERBER |
| `cargo` | CERBER |
| `safe_terrain` / `sky` | SceneSeg only |

**Forbidden types:** weapon, munition, tank-as-kill, fire-control lock (ADR-004).

## Relations

| Kind | Meaning |
|------|---------|
| `INSIDE` | Object inside sector / geofence |
| `NEAR` | Distance below threshold |
| `MOVING_TOWARD` | Closing relative velocity |
| `MOVING_AWAY` | Opening relative velocity |
| `OBSERVED_BY` | Object observed by agent_id |
| `ASSIGNED_TO` | Task/sector assigned to agent |
| `LOST_BY` | Agent lost track |
| `HANDOFF_TO` | Civil handoff to peer / operator |

```text
Relation { relation_id, kind, subject_id, object_id, confidence, stamp_s, trace_id }
```

## Events

| kind | When |
|------|------|
| `DETECTED` | First WorldObject insert |
| `UPDATED` | Pose/conf change |
| `LOST` | TTL / tracker drop |
| `ENTER_SECTOR` | INSIDE becomes true |
| `ALERT` | SceneAnalyst / policy |
| `HANDOFF` | Operator or peer take |
| `LINK_LOST` | Coordinator timeout |
| `POLICY_DENY` | MissionProfile blocked action |

```text
Event { event_id, kind, object_id, agent_id, detail, stamp_s, trace_id }
```

## SoftBus topics

| Topic | Msg |
|-------|-----|
| `/bd/dmi/world_fact` | Legacy snapshot (kept) |
| `/bd/dmi/world_object` | WorldObject |
| `/bd/dmi/relation` | Relation |
| `/bd/dmi/event` | Event |

## Migration

1. SceneFusion continues to publish `WorldFact` for compatibility.  
2. Same tick publishes `WorldObject` (object_id = fact_id).  
3. WorldCache stores both; ontology queries prefer WorldObject.  
4. Consumers (DMI, SceneAnalyst) migrate to WorldObject; fact remains projection.

## Edge vs GSC

- **Onboard:** local WorldCache + last intent if GSC lost (ADR-002).  
- **GSC:** merges OBSERVED_BY / ASSIGNED_TO across agents for COP — not required for SAFE_LOITER.
