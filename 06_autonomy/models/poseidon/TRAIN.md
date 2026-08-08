# POSEIDON — Train on NULLXES / RunPod machines

**Canon:** [POSEIDON.md](../../../00_docs/architecture/POSEIDON.md) · ADR-005 · ADR-006  
**Out:** `packs/<pack_id>/` artifacts + `sha256` — **product ids always POSEIDON / poseidon_***  
**Civil:** ADR-004 — no weapon / tank packs  
**Hub base:** only `base_repo` in pack.yaml (never pack_id)

## Naming after export

| Wrong | Right |
|-------|-------|
| `qwen3_vl_emb` pack_id | `poseidon_ve_emb_2b` |
| SoftBus model=`Qwen/...` | SoftBus model=`POSEIDON-VE-01` |

## Machine image

Use a **PyTorch CUDA host image** (RunPod PyTorch template / internal farm AMI).

| Do | Do not |
|----|--------|
| Use system / image `torch` + CUDA | `pip install torch` / `torchvision` |
| `pip install -r requirements.txt` (extras only) | Pin a second torch from PyPi |
| One pack = one dataset = one train job | Mix FLAME+Seraphim into one head without remap plan |

```bash
python -c "import torch; print(torch.__version__, torch.cuda.is_available(), torch.cuda.get_device_name(0))"
```

Suggested VRAM: ≥24 GB (4090 / L40S / RTX PRO 6000).

## Layout

```
06_autonomy/models/poseidon/
  concepts/civil_v1.yaml
  configs/                  # CV train_*.yaml
  configs/ve/ emb_2b.yaml rr_2b.yaml
  configs/vl/ scenefact_2b.yaml
  packs/<pack_id>/pack.yaml
  scripts/
    train_pack.py export_pack.py validate_registry.py runpod_pack.sh
    build_ve_pack.py train_vl_scenefact.py
```

## CV packs (detect)

```bash
export POSEIDON_DATA_ROOT=/workspace/datasets/poseidon
bash 06_autonomy/models/poseidon/scripts/runpod_pack.sh uav_seraphim
```

| Knob | UAV / fire / power |
|------|--------------------|
| model | `yolov8s.pt` |
| imgsz | 1280 UAV · 640 fire/power |
| epochs | 60–100 |
| export | imgsz 640 opset 17 |

Product names: `POSEIDON-CV-UAV-01` / `FIRE-01` / `POWER-01`.

## VE pack — `poseidon_ve_emb_2b` → POSEIDON-VE-01

Production Hub base: `Qwen/Qwen3-VL-Embedding-2B` (`load_from_hub: true`).

```bash
python 06_autonomy/models/poseidon/scripts/build_ve_pack.py \
  --config 06_autonomy/models/poseidon/configs/ve/emb_2b.yaml
```

Bakes `concepts.fp16.npy` into the pack. SoftBus model = `POSEIDON-VE-01`.  
Reranker: `poseidon_ve_rr_2b` ← `Qwen/Qwen3-VL-Reranker-2B`.

## VL pack — `poseidon_vl_scenefact_2b` → POSEIDON-VL-01

Production Hub base: `Qwen/Qwen3-VL-2B-Instruct` (fallback `Qwen2-VL-2B-Instruct`).

```bash
python 06_autonomy/models/poseidon/scripts/train_vl_scenefact.py \
  --config 06_autonomy/models/poseidon/configs/vl/scenefact_2b.yaml \
  --data "$POSEIDON_DATA_ROOT/scenefact_civil_v1"
```

LoRA SFT → adapters under pack dir. SoftBus model = `POSEIDON-VL-01`.

## FW — `poseidon_fw_gsc` → POSEIDON-FW-GSC

GSC bootstrap: pin AgentWorld under pack dir; `companion_load: false`.  
Aerial FT later: `poseidon_fw_aerial_v1` from SoftBus traces.

## Validate

```bash
python 06_autonomy/models/poseidon/scripts/validate_registry.py
```

## Forbidden

- `pip install torch*` on train hosts  
- Cloud LLM / Ollama in flight path  
- Shipping Hub names as pack_id / SoftBus model  
- Weapon / tank datasets  
