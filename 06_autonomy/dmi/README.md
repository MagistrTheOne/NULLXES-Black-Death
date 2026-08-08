# DMI v1 — Distributed Mission Intelligence

L6 mission collective layer. **L0 is swarm-blind.**

Canon: `00_docs/adr/ADR-002_DMI_V1.md` · `00_docs/architecture/DMI_V1.md`

| Module | Role |
|--------|------|
| `mission_score.py` | allocator score |
| `swarm_health.py` | ONLINE…RECOVERED |
| `world_cache.py` | Shared World Cache |
| `event_bus.py` | significant-change filter |
| `coordinator.py` | Ground Swarm Coordinator |
| `swarm_agent.py` | onboard ACCEPT/REJECT |
| `intent_bridge.py` | SwarmIntent → GoalMsg |

Soft nodes: `ros2/nodes/dmi_coordinator_soft.py`, `dmi_agent_soft.py`.

Ontology / policy (2026-08):
- `messages.WorldObject` · Relations · Events — [DMI_ONTOLOGY.md](../../00_docs/architecture/DMI_ONTOLOGY.md)
- `mission_policy.py` + `mission_profiles/*.yaml` — [MISSION_POLICY_SPEC.md](../../00_docs/architecture/MISSION_POLICY_SPEC.md)
- Trace: `perception/trace` — [TRACE_SPEC.md](../../00_docs/architecture/TRACE_SPEC.md)
