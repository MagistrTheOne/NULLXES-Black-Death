# MISSION_POLICY_SPEC — Runtime capability control

**Status:** Canon v1 · 2026-08-08  
**Refs:** [ADR-004](../adr/ADR-004_CIVIL_PRODUCT_BOUNDARY.md) · [ADR-008](../adr/ADR-008_DUAL_ENVELOPE.md) · [DMI_ONTOLOGY.md](DMI_ONTOLOGY.md) · [DMI_V1.md](DMI_V1.md) · [MODE_ENVELOPES.md](MODE_ENVELOPES.md)

## Goal

Not paper ADR alone — **runtime** MissionProfile gates actions before Guidance / L0Bridge. Same CERBER/POSEIDON/DMI/L0; envelope **CIVIL** (default) or **DEFENSE** (operator_ack). Different allowed verbs. NEVER_ACTIONS cannot be enabled by YAML.

## Envelopes

| Envelope | Boot | RID (ПП 1701 / ЭРА-ГЛОНАСС) | COP |
|----------|------|------------------------------|-----|
| `civil` | default | broadcast required | ≤ 10 km |
| `defense` | `operator_ack` | hold allowed | ≤ 50 km GSC territorial (not EO) |

Path: `06_autonomy/mission_profiles/<id>.yaml` · defense: `mission_profiles/defense/<id>.yaml`

## Actions (civil)

| Action | Meaning |
|--------|---------|
| `OBSERVE` | Ingest WorldObjects |
| `TRACK` | Maintain track_ids |
| `MAP` | Publish terrain / scene facts |
| `INSPECT` | Approach waypoint for inspection |
| `ALERT` | SceneAnalyst alerts |
| `HANDOFF` | Handoff to operator / peer |
| `LOITER` | SAFE_LOITER / guided loiter |
| `RTB` | Return / RTL request via Plane |
| `EXPLORE_SECTOR` | DMI sector explore |
| `GOTO_XYZ` | Guided goto |
| `CHASE` / `ESCORT` / `DENY_PRESENCE` | Civil track modes (ADR-004) |

**Never allowed in any profile:** weapon arm, fire-control, strike, munition bus, GNSS jam/spoof emit, `GUIDANCE_INTENT`. Hardcoded `NEVER_ACTIONS` in `dmi/mission_policy.py`.

## MissionProfile YAML

Path: `06_autonomy/mission_profiles/<profile_id>.yaml`

```yaml
profile_id: inspection.powerline.v1
version: 1
envelope: civil
expires_at: "2099-01-01T00:00:00Z"   # or omit
allowed_actions:
  - OBSERVE
  - TRACK
  - MAP
  - INSPECT
  - ALERT
  - HANDOFF
  - LOITER
  - RTB
  - GOTO_XYZ
denied_actions:
  - CHASE
allowed_models:
  - cerber:v2
  - poseidon:power_insplad
  - poseidon:uav_seraphim
require_signed_models: true
geofence:
  xmin: -5000
  xmax: 5000
  ymin: -5000
  ymax: 5000
  zmin: 0
  zmax: 400
max_agl_m: 120
cop_radius_m: 5000
rid_required: true
rid_broadcast: true
emergency_termination: RTL
registration_class: uchet
```

## Gate rules

Deny (→ Event `POLICY_DENY`, mode LOITER/RTB per FM) when:

1. Action not in `allowed_actions` or in `denied_actions`  
2. Model pack not in `allowed_models` and `require_signed_models`  
3. Goal / object outside geofence  
4. Profile expired  
5. Unsigned STABLE pack when require_signed  

## Example profiles

### `inspection.powerline.v1`

Allowed: OBSERVE, TRACK, MAP, INSPECT, ALERT, HANDOFF, LOITER, RTB, GOTO_XYZ  
Models: CERBER + power_insplad (+ uav_seraphim optional)

### `perimeter.alert.v1`

Allowed: OBSERVE, TRACK, ALERT, HANDOFF, LOITER, RTB, DENY_PRESENCE  
Denied: INSPECT approach into unknown compound without operator  
Flow: detect → classify → track → alert → handoff → operator response  
**No kinetic.** Defense profiles (`airspace.guard.v1`, `isr.territory.v1`): same verbs + `INGEST_TERRITORIAL` / `CORRELATE_IFF`. CHASE still denied. COP 30–50 km on GSC only. See [MODE_ENVELOPES.md](MODE_ENVELOPES.md).

## SoftBus

| Topic | Msg |
|-------|-----|
| `/bd/mission/profile` | Active profile id + hash + envelope |
| `/bd/mission/policy_decision` | `{action, allowed, reason, trace_id}` |
| `/bd/mission/envelope` | Committed CIVIL \| DEFENSE |
| `/bd/mission/envelope_switch` | Operator request (`operator_ack` for DEFENSE) |
| `/bd/gsc/territorial_ingest` | RID / ERA / ADS-B-like / operator track |
| `/bd/gsc/territorial_track` | COP track in radius |
| `/bd/gnss/integrity` | Own-ship jam/spoof detect |
| `/bd/rid/broadcast` | ПП 1701 / ЭРА-ГЛОНАСС shaped RID |

## Implementation

- Loader / NEVER_ACTIONS: `dmi/mission_policy.py`
- Envelope switch: `dmi/envelope.py` · `ros2/nodes/envelope_soft.py`
- Gate called from intent bridge / guidance path before publishing Goal/plane cmds.
