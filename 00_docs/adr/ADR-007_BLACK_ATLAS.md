# ADR-007 — NULLXES BLACK ATLAS (AI + coordinator)

**Status:** Accepted (product lock)  
**Date:** 2026-08-13  
**Deciders:** Maga / NULLXES systems  
**Refs:** [ADR-002](ADR-002_DMI_V1.md) · [ADR-006](ADR-006_POSEIDON_FAMILY.md) · [BLACK_ATLAS.md](../architecture/BLACK_ATLAS.md)

## Context

DMI v1 GroundSwarmCoordinator is a deterministic Mission Score allocator. POSEIDON-FW-GSC (AgentWorld-35B) is a world-model bootstrap, not a swarm allocator. CERBER is vision. The GSC needs an AI coordinator that ranks tasks, reallocates on LOST, and merges COP — without putting a chat LLM on the companion or into CERBER.

## Decision

1. **BLACK ATLAS** is a new GSC product: AI + coordinator. Not a CERBER/POSEIDON pack. Not L0.
2. **CERBER remains vision.** No Llama, Gemini, GPT, Ollama, or cloud LLM in CERBER / `perception/`.
3. **Own net.** ATLAS-ALLOC is a NULLXES-written bipartite scorer (DeepSets / Set Transformer / GAT as *architecture corpses only*). No Qwen/Llama/Gemini/GPT weights. No Hub coordinator LLM.
4. **DMI stays the executor.** ATLAS emits `AllocationPlan`. DMI still issues exclusive `TaskOffer` and accepts `TaskClaim`.
5. **Companion load = false.** ATLAS does not fly on the ship. Loss of ATLAS/GSC → last accepted SwarmIntent + local FM (ADR-002).
6. **No LangChain / LlamaIndex / Ollama / Gemini / OpenAI / Qwen Hub** in the ATLAS path. SoftBus + PyTorch train → ONNX Runtime infer.
7. **MARL onboard remains forbidden** (ADR-002). Offline imitation / distill on GSC traces is allowed.
8. **Civil + military UAV** uses NULLXES nets end-to-end. CERBER remains vision. ATLAS is coordinator, not a detector.

## Consequences

- New package `06_autonomy/atlas/` + packs `06_autonomy/models/atlas/`.
- SoftBus topics `/bd/atlas/*`.
- POSEIDON-FW-GSC (Qwen AgentWorld) is **not** ATLAS and is **debt** vs NULLXES-net lock; ATLAS does not load it.
- Naming: `atlas_*` / `BLACK-ATLAS-*`. No Hub `base_repo` for ALLOC.
