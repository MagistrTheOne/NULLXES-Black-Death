# Product lines — BLACK DEATH

**Canon:** [ADR-001](adr/ADR-001_ALPHA_ARCHITECTURE_DEMONSTRATOR.md)

```
BLACK DEATH (civil infrastructure flying platform)

    Alpha 5×5
    ROLE: System Architecture Demonstrator
    STATUS: LOCKED until Flight-1 + lessons learned
              │
     Architecture Verified
              │
      ┌───────┴────────┐
      ▼                ▼
 Beta-Endurance    Beta-Heavy
 (time / range)    (volume / payload / infra ops)
```

| Line | Goal | Touches airframe? | Touches autonomy canon? |
|------|------|-------------------|-------------------------|
| Alpha | Prove integrated system + fault behaviour | Frozen | Build / verify |
| Beta-Endurance | Max endurance / range | Yes (AR, span, energy) | Port, don't redesign |
| Beta-Heavy | Payload, volume, infrastructure work | Yes (thick BWB, hardpoints) | Port, don't redesign |

Full ~50×50 product may **compose** lessons from both Betas; it does not reopen Alpha geometry.
