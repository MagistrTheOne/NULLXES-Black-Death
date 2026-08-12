# NULLXES BLACK ATLAS

**Status:** LOCKED naming · ADR-007  
**Product:** GSC AI + coordinator  
**Not:** CERBER · POSEIDON pack · chat LLM on companion · Llama/Gemini/Ollama in flight path

```text
CERBER        SENSE     vision (ONNX detect)     — no LLM
POSEIDON      SPECIALIZE facts (CV/VE/VL/FW)
DMI           DECIDE     policy + exclusive offer/claim
BLACK ATLAS   COORDINATE GSC AI → AllocationPlan → DMI
Guidance/L0   ACT        setpoints only
```

## Placement

```text
agents: CERBER → POSEIDON → WorldObject/Fact → SwarmAgent
                                              │ /bd/dmi/agent_status
                                              │ /bd/dmi/world_object
                                              ▼
GSC host
  ┌─────────────────────────────────────────┐
  │ BLACK ATLAS                             │
  │   ALLOC  ONNX scorer  → AllocationPlan  │
  │   BRIEF  optional SLM → CopBrief JSON   │
  │   COP    merge OBSERVED_BY/ASSIGNED_TO  │
  └──────────────────┬──────────────────────┘
                     │ /bd/atlas/plan
                     ▼
  DMI GroundSwarmCoordinator  (executor, exclusive TaskOffer)
                     │
                     ▼
              /bd/dmi/task_offer + /bd/dmi/intent
```

ATLAS **proposes**. DMI **executes**. L0 **не знает** ни ATLAS, ни рой.

## Own net (LOCKED)

Weights, train loop, export, sha — **NULLXES**.  
Architecture corpses (not Hub checkpoints): DeepSets, Set Transformer, Pointer-Net, GAT bipartite.

| Forbidden as ATLAS weights | Why |
|----------------------------|-----|
| Qwen / Llama / Gemini / GPT / Ollama | чужой корпус + чужие веса |
| POSEIDON-FW AgentWorld-35B | другой job (WorldDelta), не аллокатор |
| Chat decoder as coordinator | нет схемы, нет p95, нет fail-closed |

v1 = **ATLAS-ALLOC only**. BRIEF — отдельная NULLXES-сеть позже, не чужой SLM.

## Lightweight model (ALLOC) — the coordinator

**Product:** `BLACK-ATLAS-ALLOC-01`  
**pack_id:** `atlas_alloc_v1`  
**Params:** 2–8 M  
**Artifact:** `model.onnx` + sha256, INT8 or FP16  
**Runtime:** ONNX Runtime on GSC CPU (default) / CUDA if present  
**Budget:** p95 ≤ 10 ms CPU, ≤ 3 ms CUDA  
**VRAM:** 0 on companion; GSC < 256 MB

### Architecture

Bipartite set-encoder (DeepSets / tiny transformer), not a decoder LLM.

```text
Agents  [N, Fa] ──► AgentEnc ──┐
Sectors [M, Fs] ──► SectorEnc ─┼─► CrossScore [N, M]
World   [K, Fw] ──► WorldPool ─┘         │
                                         ▼
                              AllocationHead
                                score[n,m]
                                reallocate[n]     # LOST / LIMITED
                                hold[m]           # no offer this tick
```

| Tensor | Features |
|--------|----------|
| Agent | x,y,z, soc, payload_frac, health_factor, has_intent, dist_to_assigned, link_ok |
| Sector | x,y,z, assigned_onehot, object_count, alert_count, last_visit_age_s |
| World pool | counts by type (uav, human, fire, vehicle, …), max_conf, mean_cov |

Fixed caps: `N≤16`, `M≤32`, `K≤64`. Pad + mask. No variable chat context.

### Output schema (`AllocationPlan`)

```text
AllocationPlan {
  plan_id, stamp_s, trace_id, model: "BLACK-ATLAS-ALLOC-01"
  assignments: [{ agent_id, sector_id, intent_kind, score, reason_code }]
  releases:    [{ agent_id, task_id, reason_code }]   # LOST / REJECT timeout
  holds:       [sector_id]
}
```

`intent_kind` ∈ `EXPLORE_SECTOR` | `GOTO_XYZ` | `LOITER` (DMI IntentKind).  
`reason_code` ∈ `SCORE` | `REALLOC_LOST` | `REALLOC_LIMITED` | `COP_ALERT` | `HOLD`.

DMI maps each assignment → exclusive `TaskOffer`. If offer already open, ATLAS tick is skipped (DMI invariant).

### Train (GSC offline)

```text
1. Teacher: current Mission Score (mission_score.py) on recorded AgentStatus+Sectors
2. Labels+: operator overrides from FlightRecorder / GSC UI
3. Loss: assignment CE + ranking (pairwise) + realloc BCE
4. Export: PyTorch → ONNX opset 17 → sha → registry STABLE
```

No MARL onboard. Offline distill only.

## BRIEF (later, own net)

Not in v1. If added: NULLXES-trained schema encoder → `CopBrief` JSON. Same ban: no Qwen/Llama/Gemini weights. `companion_load: false`.

## Stack

| Layer | Choice |
|-------|--------|
| Language | Python 3.11 (same as L1–L6) |
| Bus | SoftBus `/bd/atlas/*` |
| ALLOC train | PyTorch 2.x in-repo (`models/atlas/`) |
| ALLOC infer | ONNX Runtime (`CPUExecutionProvider`, CUDA optional) |
| Pack/release | MODEL_RELEASE_SPEC (sha, STABLE, fail-closed) |
| Executor | existing `dmi/coordinator.py` |
| Trace | FlightRecorder `trace_id` |
| Forbidden | LangChain, LlamaIndex, Ollama, Gemini, OpenAI cloud, Qwen Hub weights, HuggingChat |

## SoftBus

| Topic | Payload | Direction |
|-------|---------|-----------|
| `/bd/atlas/plan` | AllocationPlan | ATLAS → DMI |
| `/bd/atlas/cop` | CopSnapshot (objects+relations+agents) | ATLAS internal / UI |
| `/bd/atlas/brief` | CopBrief | ATLAS-BRIEF → operator |
| `/bd/atlas/health` | model_id, p95_ms, sha_ok | ATLAS → GSC |

ATLAS **subscribes:** `/bd/dmi/agent_status`, `/bd/dmi/swarm_health`, `/bd/dmi/world_object`, `/bd/dmi/relation`, `/bd/dmi/event`, `/bd/dmi/task_claim`.  
ATLAS **does not subscribe** cameras. Vision stays CERBER.

## Code layout (when Maga says implement)

```text
06_autonomy/atlas/
  messages.py          AllocationPlan, CopSnapshot, CopBrief
  cop_merge.py         OBSERVED_BY / ASSIGNED_TO COP
  alloc_runtime.py     ORT session, fail-closed sha
  planner.py           CopSnapshot → AllocationPlan
  dmi_adapter.py       AllocationPlan → coordinator.allocate_* / on_claim
  brief_runtime.py     optional, companion_load false
06_autonomy/models/atlas/packs/atlas_alloc_v1/
  pack.yaml            sha, onnx_layout: atlas_bipartite_v1
  model.onnx
```

## Invariants

1. CERBER = vision. No LLM in CERBER.
2. ATLAS never publishes `GuidanceIntent` or `/bd/l0/setpoint`.
3. ATLAS never loads on companion (`companion_load: false`).
4. DMI exclusive offer/claim unchanged.
5. GSC/ATLAS loss → last SwarmIntent + FM (SAFE_LOITER / RTB).
6. pack_id / SoftBus model never `llama*`, `gemini*`, `gpt*`, `qwen*`, `ollama*`.
7. L0 swarm-blind.

## KPI

| Pack | Gate |
|------|------|
| ALLOC | assignment match vs Mission Score teacher ≥ 0.9 on holdout; p95 ≤ 10 ms; sha |
| ALLOC+operator | realloc on LOST within 1 tick of health LOST |
| BRIEF | JSON schema validity ≥ 0.99; no Guidance fields in output |
