# ATLAS-ALLOC — RunPod train + SIL before GSC hardware

**Canon:** [BLACK_ATLAS.md](../../../00_docs/architecture/BLACK_ATLAS.md) · ADR-007  
**Product:** `BLACK-ATLAS-ALLOC-01` · `pack_id: atlas_alloc_v1`  
**Not:** CERBER · POSEIDON · chat LLM · companion load · H100 job

Teacher = `dmi/mission_score.py`. No pictures. No Qwen/Llama/Gemini.

---

## GPU (LOCKED for ALLOC)

| Job | Pod | Why |
|-----|-----|-----|
| **ATLAS-ALLOC** | **1× RTX 4090 24GB** (or leftover on **RTX PRO 6000 Blackwell**) | 2–8M params, tables only |
| CERBER detect | RTX PRO 6000 BW (existing) | imgsz 1280 |
| ATLAS-BRIEF | H100 later | not v1 |
| H100 / H200 / A100 | **do not rent for ALLOC** | waste |

**Image:** `runpod/pytorch:1.0.2-cu1281-torch280-ubuntu2404`  
Torch from image. Do not `pip install torch`. Disk 20 GB.

---

## Phase 0 — pod (you spin this)

```bash
cd /workspace
git clone https://github.com/MagistrTheOne/NULLXES-Black-Death.git
cd NULLXES-Black-Death
bash 06_autonomy/models/atlas/scripts/runpod_alloc.sh
```

Script: synth teacher → `alloc_v1.pth` → `model.onnx` → sha256 → val argmax-match vs teacher.

**Gate CANDIDATE (L1, 2026-08-13):** `model.onnx` sha `5be276669affd2c2a33429f9f0592eb432f0a7dda0638cbe6a5c42f084e501c6`, val_argmax_match **0.9716** (gate 0.90). Weights stay out of git.  
**Gate STABLE:** onnx on GSC at pack path + p95 `plan()` ≤ 10 ms CPU + ORT path in `planner.py`. Until then `runtime.py` does not load (`release_channel: CANDIDATE`).

Download home: `/workspace/atlas/model.onnx` + sha. Weights stay out of git.

Manual:

```bash
python 06_autonomy/models/atlas/scripts/train_alloc.py \
  --config 06_autonomy/models/atlas/configs/alloc_v1.yaml \
  --out    /workspace/atlas/alloc_v1.pth

python 06_autonomy/models/atlas/scripts/export_alloc.py \
  --config  06_autonomy/models/atlas/configs/alloc_v1.yaml \
  --weights /workspace/atlas/alloc_v1.pth \
  --out     /workspace/atlas/model.onnx
```

Config: N=16, M=32, hidden=64, pairwise Δxy, CE-only, samples=4096, epochs=40 (early-stop at gate).

---

## Dataset (not CV)

```text
Agent  [N≤16, 9]  x,y,z, soc, payload, health, has_intent, dist_assigned, link_ok
Sector [M≤32, 8]  x,y,z, assigned, n_obj, n_alert, last_visit_age, pad
Label  [N, M]     score_agent(distance, soc, payload, health)
```

On-disk later (gitignored): `06_autonomy/models/datasets/atlas/alloc_teacher_v1/{train,val}.npz`  
Phase 0 generates in RAM. Phase 1 dumps npz + pad-mask. Phase 2 = FlightRecorder CopSnapshot.jsonl.

---

## SIL ladder (metrics before our iron)

Gazebo / AirSim / `soft_runtime` = BLOCKED twins. Do not fake a world.

| Layer | What | Gate |
|-------|------|------|
| L0 unit | `10_tests/unit` | already green |
| L1 teacher-val | holdout on pod | argmax match ≥ 0.90 |
| L2 swarm-SIL | SoftBus N agents × M sectors | exclusive offer=1; REJECT→other agent 1 tick; ATLAS never `/bd/l0/setpoint`; no cam subscribe |
| L3 ship-SIL | `tools/flight1_bench_chain.py` | 1 airframe SensorHub→Goal→Plane; ATLAS off |
| L4 vision | CERBER Studio | mAP/ID-switch; not ALLOC |
| L5 HIL | dual A/B + FC | failover ≤500 ms |
| L6 practice | edu → AR Wing | 1 agent, ATLAS on GSC only |

L2 script (next commit, not this pod): `06_autonomy/tools/atlas_swarm_sil.py`  
Inject: REJECT, offer timeout 2s, SOC drop, agent drop (LOST), `link_ok=0`. Kinematic `xy += 0.1*(goal-xy)`. JSON report.

---

## Land on our hardware

```text
1. GSC x86  atlas_soft + dmi_coordinator_soft
            using_onnx=False until STABLE
2. 1 practice airframe  CERBER+DMI+Guidance+L0; ATLAS on ground
3. N=3 same GSC
4. Orin companion  ATLAS never loads (companion_load: false)
```

---

## Invariants

1. ATLAS proposes `AllocationPlan`. DMI exclusive TaskOffer/claim.
2. No cameras in `atlas_soft`.
3. No GuidanceIntent / `/bd/l0/setpoint` from ATLAS.
4. L0 swarm-blind.
5. Pack never `qwen*`/`llama*`/`gemini*`/`gpt*`/`ollama*`.
