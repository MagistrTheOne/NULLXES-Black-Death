# POSEIDON — Train on NULLXES / RunPod machines

**Canon:** [POSEIDON.md](../../../00_docs/architecture/POSEIDON.md) · ADR-005  
**Out:** `packs/<pack_id>/model.onnx` + `sha256` in `pack.yaml`  
**Civil:** ADR-004 — no weapon / tank packs

## Machine image

Use a **PyTorch CUDA host image** (RunPod PyTorch template / internal farm AMI).

| Do | Do not |
|----|--------|
| Use system / image `torch` + CUDA | `pip install torch` / `torchvision` |
| `pip install -r requirements.txt` (extras only) | Pin a second torch from PyPI |
| One pack = one dataset = one train job | Mix FLAME+Seraphim into one head without remap plan |

Verify before train:

```bash
python -c "import torch; print(torch.__version__, torch.cuda.is_available(), torch.cuda.get_device_name(0))"
```

Suggested VRAM: ≥24 GB (4090 / L40S / RTX PRO 6000). Disk depends on dataset.

## Layout

```
06_autonomy/models/poseidon/
  requirements.txt          # NO torch
  TRAIN.md                  # this file
  configs/
    train_uav_seraphim.yaml
    train_fire_flame.yaml
    train_power_insplad.yaml
  packs/<pack_id>/pack.yaml
  scripts/
    train_pack.py
    export_pack.py
    validate_registry.py
    runpod_pack.sh
```

## One-shot (pod / farm)

```bash
cd /workspace
git clone https://github.com/MagistrTheOne/NULLXES-Black-Death.git
cd NULLXES-Black-Death

# Torch already on image — only Ultralytics + hub + onnx extras
pip install -r 06_autonomy/models/poseidon/requirements.txt

export HF_TOKEN=hf_...                    # if gated datasets
export POSEIDON_DATA_ROOT=/workspace/datasets/poseidon

# Example: UAV specialist (P0)
bash 06_autonomy/models/poseidon/scripts/runpod_pack.sh uav_seraphim
```

`runpod_pack.sh <pack_id>`:

1. Assert `torch` importable (fail if missing — install via image, not pip torch)
2. Prepare YOLO data tree under `$POSEIDON_DATA_ROOT/<pack_id>/`
3. `train_pack.py` — Ultralytics detect FT
4. `export_pack.py` — ONNX opset 17 + sha into `pack.yaml`

## Manual per pack

### P0 — `uav_seraphim`

Dataset: Seraphim (HF) and/or DUT / UETT4K YOLO trees. Single class `uav` → remap `0→2` at export/runtime (`cerber_remap` in pack.yaml).

```bash
export POSEIDON_DATA_ROOT=/workspace/datasets/poseidon
PACK=uav_seraphim

# Data: YOLO layout with names: ['uav']  (nc=1)
# $POSEIDON_DATA_ROOT/uav_seraphim/data.yaml

python 06_autonomy/models/poseidon/scripts/train_pack.py \
  --train-config 06_autonomy/models/poseidon/configs/train_uav_seraphim.yaml \
  --data "$POSEIDON_DATA_ROOT/uav_seraphim/data.yaml"

python 06_autonomy/models/poseidon/scripts/export_pack.py \
  --pack uav_seraphim \
  --weights runs/detect/poseidon-uav_seraphim/weights/best.pt
```

Reuse CERBER data prep for Seraphim if needed:

```bash
export CERBER_V2_ROOT=/workspace/datasets/cerber_v2
python 06_autonomy/models/cerber_v2/scripts/prepare_data.py --root "$CERBER_V2_ROOT" --full-seraphim
# then point train data.yaml at UAV-only slice or remap labels to single class 0=uav
```

### P1 — `fire_flame` / `power_insplad`

Same flow, configs:

- `configs/train_fire_flame.yaml` — FLAME → class `fire`
- `configs/train_power_insplad.yaml` — InsPLAD/MPID → class `power_line`

Place YOLO trees:

```
$POSEIDON_DATA_ROOT/fire_flame/{images,labels}/{train,val}/ + data.yaml
$POSEIDON_DATA_ROOT/power_insplad/{images,labels}/{train,val}/ + data.yaml
```

## Train knobs (defaults in yaml)

| Knob | UAV / fire / power |
|------|--------------------|
| model | `yolov8s.pt` (image torch) |
| imgsz | 1280 UAV · 640 fire/power |
| epochs | 60–100 |
| batch | fit VRAM (16 @ 1280 on 48GB; drop on 24GB) |
| export | imgsz 640 opset 17 |

## After export — companion load

```bash
python 06_autonomy/models/poseidon/scripts/validate_registry.py
# pack.yaml sha256 != pending  →  PoseidonRuntime loads ORT session
```

Flight: CERBER generalist + router enables pack (`AIRSPACE_GUARD` / CERBER hints).

## Explicitly forbidden

- `pip install torch*` on train hosts  
- Cloud LLM / Ollama in train or runtime  
- Weapon / tank datasets (civil reject in `registry/registry.yaml`)
