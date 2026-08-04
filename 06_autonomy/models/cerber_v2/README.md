# CERBER V2 — RunPod pack (bare metal, no Docker)

**Product:** NULLXES CERBER detect — defensive pursuit eyes (`uav=2` boost).  
**Not:** armed stack · not CERBER RT robot · not Docker image.  
**Out:** `detector_alpha_v2b.onnx` + sha256 in `configs/detector_alpha_v2b.yaml`  
**Canon:** `00_docs/architecture/CERBER.md` · `CERBER_DATASETS.md`

## Pod image

Use a **RunPod PyTorch** template (CUDA + torch preinstalled), e.g. torch 2.8 / cu12.x Ubuntu.  
Do **not** wrap this pack in Docker.

Suggested: ≥24 GB VRAM (4090 / L40S / RTX PRO 6000 / A100-40). Disk ≥150 GB.

## One-shot (on pod)

```bash
cd /workspace
git clone https://github.com/MagistrTheOne/NULLXES-Black-Death.git
cd NULLXES-Black-Death

# optional gated / faster HF
export HF_TOKEN=hf_...          # if you have it
export CERBER_V2_ROOT=/workspace/datasets/cerber_v2

pip install -r 06_autonomy/models/cerber_v2/requirements.txt

# prepare data + train + export
bash 06_autonomy/models/cerber_v2/scripts/runpod_all.sh
```

Steps inside `runpod_all.sh`:

1. `prepare_data.py` — VisDrone + Seraphim `--full` + HF UAV extras → YOLO tree  
2. `train.py` — resume from Hub CERBER-CV-v2 or local `best.pt`  
3. `export_onnx.py` — flight ONNX + sha256  

## Manual (debug)

```bash
export CERBER_V2_ROOT=/workspace/datasets/cerber_v2
python 06_autonomy/models/cerber_v2/scripts/prepare_data.py --root "$CERBER_V2_ROOT" --full-seraphim
python 06_autonomy/models/cerber_v2/scripts/train.py --data "$CERBER_V2_ROOT/data.yaml"
python 06_autonomy/models/cerber_v2/scripts/export_onnx.py \
  --weights runs/detect/cerber-detect/v2-pursuit/weights/best.pt
```

## DUT / UETT4K (manual drop-in)

Not on HF. After download, place YOLO trees:

```
$CERBER_V2_ROOT/sources/dut_anti_uav/{images,labels}/{train,val}/
$CERBER_V2_ROOT/sources/uett4k/{images,labels}/{train,val}/
```

Then:

```bash
python 06_autonomy/models/cerber_v2/scripts/prepare_data.py --root "$CERBER_V2_ROOT" \
  --skip-visdrone --skip-seraphim --merge-local-uav
```

DUT: https://github.com/wangdongdut/DUT-Anti-UAV  
UETT4K: https://github.com/mugheessarwarawan/UETT4K-Anti-UAV (SharePoint)

## Init weights

Default train config pulls Hub `MagistrTheOne/CERBER-CV-v2` → `best.pt` if local Stage-1/v2 missing.  
Override: `--weights /path/to/best.pt`

## Host smoke (PC webcam, after ONNX home)

```bash
python 06_autonomy/models/scripts/webcam_cerber_smoke.py --v2
# after v2b lands locally, point VisionPipeline at detector_alpha_v2b.yaml
```

## Layout

```
cerber_v2/
  README.md
  requirements.txt
  configs/
    train.yaml
    data.yaml                 # template; prepare rewrites path=
    detector_alpha_v2b.yaml   # flight; sha256 filled by export
  scripts/
    prepare_data.py
    train.py
    export_onnx.py
    runpod_all.sh
    fetch_hf_extras.py
  sources/.gitkeep            # downloads live on pod, not in git
```
