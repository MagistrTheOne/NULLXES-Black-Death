# Product lines — BLACK DEATH

**Canon:** [ADR-001](adr/ADR-001_ALPHA_ARCHITECTURE_DEMONSTRATOR.md) · [ADR-002 DMI](adr/ADR-002_DMI_V1.md)

```
BLACK DEATH (civil infrastructure flying platform)

    Alpha 5×5  «Black Judgment»
    ROLE: System Architecture Demonstrator
    STATUS: LOCKED until Flight-1 + lessons learned
              │
     Architecture Verified
              │
      ┌───────┴────────┐
      ▼                ▼
 Beta-Endurance    Beta-Heavy
 (time / range)    (volume / payload / infra ops)

    DMI v1 (L6) — Distributed Mission Intelligence
    N× Judgment-class / practice airframes (not N× 50×50)
    PRACTICE: edu (~Aug 2026) → SonicModell AR Wing Pro (~Sep 2026)
```

| Line | Name | Goal | Touches airframe? | Touches autonomy canon? |
|------|------|------|-------------------|-------------------------|
| Alpha | **Black Judgment** (5×5) | Prove integrated system + fault behaviour | Frozen | Build / verify |
| CERBER | perception system | Vision·detect·fusion·… (YOLO is an organ) | Sensors / ONNX | `perception/` |
| DMI | multi-agent mission layer | Tasks / sectors / world cache; L0 swarm-blind | Practice frames first | Add L6; do not redesign L0 |
| ATLAS | GSC AI + coordinator | AllocationPlan → DMI executor; COP merge | GSC host only | `06_autonomy/atlas/`; not CERBER, not companion |
| Envelope | CIVIL \| DEFENSE | Same L0; MissionProfile switch; 30–50 km GSC COP | GSC + policy YAML | [ADR-008](adr/ADR-008_DUAL_ENVELOPE.md) · [MODE_ENVELOPES.md](architecture/MODE_ENVELOPES.md) |
| Product | **BLACK DEATH** (~50×50) | Civil infrastructure platform | After Beta | Port, don't redesign |
| Beta-Endurance | — | Max endurance / range | Yes (AR, span, energy) | Port, don't redesign |
| Beta-Heavy | — | Payload, volume, infrastructure work | Yes (thick BWB, hardpoints) | Port, don't redesign |

Full ~50×50 product may **compose** lessons from both Betas; it does not reopen Alpha geometry.
