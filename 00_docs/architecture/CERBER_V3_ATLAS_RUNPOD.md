# CERBER V3 + ATLAS-ALLOC — RunPod approach

**Status:** PLAN · 2026-08-13 · Maga  
**Do not start pod until this file is the runbook.**  
**Not:** YOLO26 · H100 · Hub LLM · weapons sets · overwrite `detector_alpha_v2b.onnx`

```text
1× GPU pod  (PyTorch CUDA image)
    Job A  CERBER V3 detect FT     hours
    Job B  ATLAS-ALLOC distill     minutes   (same GPU, after A)
```

---

## GPU / image (before launch)

| | Pick |
|--|------|
| Type | **Pod**, not serverless |
| GPU | **1× RTX 4090 24GB** (or leftover RTX PRO 6000). Not H100 for this pair |
| Disk | **≥200 GB** (Seraphim `--full` ~9 GB + VisDrone + extras) |
| Volume | network volume `/workspace/datasets` so restart does not re-download |
| Image | `runpod/pytorch:1.0.2-cu1281-torch280-ubuntu2404` |
| Torch | from image. **Do not** `pip install torch` |
| Env | `HF_TOKEN` if gated/rate-limit |

ATLAS is 2–8M table params. Renting a second pod is waste.

---

## CERBER V3 (what changes vs V2)

| | V2 | V3 |
|--|----|----|
| Out | `detector_alpha_v2b.onnx` | **`detector_alpha_v3.onnx`** (new file) |
| Init | Hub `MagistrTheOne/CERBER-CV-v2` | **v2b `best.pt`** else same Hub |
| Head nc=13 | locked ids | **same ids — do not reorder** |
| Trained slots | 0,1,2 | **0,1,2 + 5 power_line** (+10 fire if drop-in) |
| Layout | `yolo_v8_raw` | same. YOLO26 still gated |
| imgsz | 1280 train / 640 export | same |

---

## Datasets (HF search 2026-08-13)

### IN — this pod

| Source | Hub / where | CERBER id | Notes |
|--------|-------------|-----------|-------|
| VisDrone-DET | existing `prepare_cerber_data.py` (not Voxel51 mirror) | 0 human, 1 vehicle | keep mix or 0/1 die |
| Seraphim | [`lgrzybowski/seraphim-drone-detection-dataset`](https://huggingface.co/datasets/lgrzybowski/seraphim-drone-detection-dataset) | 2 uav | `--full` |
| pathikg drones | [`pathikg/drone-detection-dataset`](https://huggingface.co/datasets/pathikg/drone-detection-dataset) | 2 | 54k rows, viewer OK |
| bird hard-neg | [`matisdsp/drone-bird-detection-dataset`](https://huggingface.co/datasets/matisdsp/drone-bird-detection-dataset) | empty labels | 799 imgs |
| ybli YOLO drones | [`ybli/yolo-drone-detection`](https://huggingface.co/datasets/ybli/yolo-drone-detection) | 2 | viewer weak; skip if 0 pairs |
| **powerline** | [`docmhvr/powerline-components-and-faults`](https://huggingface.co/datasets/docmhvr/powerline-components-and-faults) | **5** | 1912, MIT, xyxy→YOLO, **all source classes → 5** |

### IN — manual drop (not HF)

| Source | Class | If missing |
|--------|-------|------------|
| DUT Anti-UAV (GDrive) | 2 | skip |
| UETT4K (SharePoint) | 2 | skip |
| FLAME / FLAME2 (IEEE DataPort) | **10 fire** | **skip — not on Hub** |

### OUT — not this detect job

| Hub | Why |
|-----|-----|
| `lll-a-p/fpv-drone-detection-dataset` | **0 rows** |
| `CornBac0n/Anti-UAV-RGBT` | video/IR track, not DET boxes |
| `chloechia/loveda` · `isaaccorley/landcoverai` | **seg lane**, not YOLO boxes this pod |
| `romainpuech/wildfire-drone-routing-data` | routing, not fire DET |
| tank / weapon DET | civil lock |

---

## ATLAS-ALLOC (unchanged job)

Teacher = `dmi/mission_score.py`. No pictures.  
Script already: `06_autonomy/models/atlas/scripts/runpod_alloc.sh`  
Out: `/workspace/atlas/model.onnx` · CANDIDATE until val match ≥ 0.90.

---

## Pod sequence (after you start the machine)

```bash
cd /workspace
git clone https://github.com/MagistrTheOne/NULLXES-Black-Death.git
cd NULLXES-Black-Death
export HF_TOKEN=hf_...
export CERBER_V3_ROOT=/workspace/datasets/cerber_v3
bash 06_autonomy/models/cerber_v3/scripts/runpod_v3_then_atlas.sh
```

Inside:

1. `cerber_v2/prepare_data.py` → VisDrone + Seraphim full + HF extras + DUT/UETT if present  
2. `cerber_v3/fetch_powerline.py` → id **5** merge  
3. `cerber_v2/train.py --train-config cerber_v3/configs/train.yaml`  
4. export **`detector_alpha_v3.onnx`** (leave v2b)  
5. `atlas/scripts/runpod_alloc.sh`  
6. **stop pod**

Copy home: `detector_alpha_v3.onnx` + yaml sha · `atlas/model.onnx` + sha. Not git.

---

## Gates

| Pack | CANDIDATE | STABLE |
|------|-----------|--------|
| CERBER V3 | ONNX + sha, layout `yolo_v8_raw` | val mAP50 on **uav** ≥ v2b; **power_line** mAP50 > 0.25; human/vehicle not collapsed |
| ATLAS | onnx exists | teacher argmax ≥ 0.90, `plan()` p95 ≤ 10 ms CPU |

Flight stays on **v2b** until V3 STABLE. ATLAS stays CANDIDATE until SIL L1.
