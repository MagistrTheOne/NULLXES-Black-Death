# ADR-005 — POSEIDON Specialist Agent Runtime

**Status:** Accepted  
**Date:** 2026-08-08  
**Deciders:** NULLXES systems architecture  
**Refs:** [POSEIDON.md](../architecture/POSEIDON.md) · [ADR-004](ADR-004_CIVIL_PRODUCT_BOUNDARY.md) · [CERBER.md](../architecture/CERBER.md)

## Context

CERBER is a generalist 13-class Detect head. Domain accuracy (UAV tiny targets, fire, power lines) needs dataset-specific specialists without breaking locked class ids or introducing cloud LLM agents.

## Decision

Introduce **POSEIDON** — local specialist agent runtime:

1. **Pack** = one dataset → one ONNX (+ sha256) + `pack.yaml` with `cerber_remap` into locked CERBER class ids.
2. **Router v1** = rule/score gates from mission mode + CERBER hints + per-frame pack budget (`budget_ms`, max K packs). No LLM.
3. **Runtime** = reuse `OrtSessionFactory` / `yolo_v8_raw` decoder unless a pack ADR changes layout.
4. **Merge** specialist detections into CERBER id space → Track → Fusion → WorldFact.
5. **Fail-closed** on sha256 mismatch or missing ONNX (pack skipped or BLOCKED at load if required).
6. **Escalation** only to NULLXES GPU servers (train/export/registry), never public inference APIs.
7. Civil boundary from ADR-004 applies to every pack.

### Explicitly out of POSEIDON v1

Ollama, cloud LLM routers, weapon packs, YOLO26 e2e layout without separate ADR.

## Consequences

- Package `06_autonomy/poseidon/` + manifests under `06_autonomy/models/poseidon/`.
- SoftBus topics `/bd/poseidon/*`.
- Companion FPS budget enforced in router; CI smoke for pack load.
