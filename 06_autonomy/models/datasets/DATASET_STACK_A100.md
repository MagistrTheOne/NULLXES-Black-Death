# Dataset stack — aerial detect → A100 train → local ONNX

**Goal:** merge public UAV/aerial sets into YOLO format, train on A100, export with `scripts/export_yolo_onnx.py` for onboard ORT.  
**Perception system:** **NULLXES CERBER** ([CERBER.md](../../../00_docs/architecture/CERBER.md))  
**Detect weights / runs:** `cerber-detect` (YOLO inside CERBER; not the product name)  
**Refs:** [VisDrone](https://docs.ultralytics.com/datasets/detect/visdrone/) · [Ultralytics install](https://docs.ultralytics.com/ru/quickstart) · UAVDT / DOTA / UETT4k (external)

Civil use only. Anti-UAV public sets are used only as **air traffic / other-UAV / obstacle** labels — not weapons.

---

## 1. Canonical class taxonomy (CERBER detect v1)

Folder names you proposed → **stable class ids** for YOLO `data.yaml`.  
Keep ids frozen once training starts.

| id | class | Your folder | Notes |
|----|-------|-------------|-------|
| 0 | `human` | Humans | person / pedestrian / people |
| 1 | `vehicle` | Vehicles | car, van, truck, bus, motor, bicycle→optional |
| 2 | `uav` | UAV | other aircraft in frame (civil awareness) |
| 3 | `landing_zone` | Landing Zones | pads / marked LZ (often **custom** labels) |
| 4 | `obstacle` | Obstacles | generic hard obstacle if not mapped elsewhere |
| 5 | `power_line` | Power Lines | wires / pylons (often OBB→AABB convert) |
| 6 | `road` | Roads | road segments / carriageway |
| 7 | `building` | Buildings | structures |
| 8 | `forest` | Forest | vegetation canopy |
| 9 | `water` | Water | rivers / lakes |
| 10 | `fire` | Fire | smoke/fire (safety / disaster) |
| 11 | `infrastructure` | Infrastructure | towers, industrial, misc infra not in 5–7 |
| 12 | `cargo` | *(optional)* | packages / pallets — mostly **custom** |

**Alpha flight yaml today** (`detector_alpha.yaml`) still lists 5 classes. After CERBER detect train, either:

- remap export to those 5 (collapse), or  
- bump `classes:` in config to the table above and re-export ONNX (preferred for DMI world facts).

---

## 2. Public datasets → which classes they feed

| Source | URL / access | Approx scale | Maps into CERBER ids | License note |
|--------|--------------|--------------|-------------------------|--------------|
| **VisDrone2019-DET** | [Ultralytics VisDrone](https://docs.ultralytics.com/datasets/detect/visdrone/) | ~8.6k images DET; auto YOLO via `VisDrone.yaml` (~2 GB) | 0 human, 1 vehicle | cite TPAMI VisDrone; AGPL tools |
| **UAVDT** | [DatasetNinja UAVDT](https://datasetninja.com/uavdt) | UAV traffic / vehicle-heavy | 1 vehicle (human if present) | check original UAVDT terms before redistribute |
| **DOTA** | [DatasetNinja DOTA](https://datasetninja.com/dota) · Ultralytics OBB | large aerial OBB | 1 vehicle, 6 road*, 7 building, 5 power_line*, 11 infrastructure | OBB→AABB or train OBB then convert; *subset of DOTA cats |
| **UETT4k Anti-UAV** | HF `mugheessarwarawan/UETT4k-Anti-UAV` | UAV-centric | 2 uav | civil remap only; verify HF license |

\*DOTA category names vary by version (plane, ship, storage-tank, baseball-diamond, …). Map only clear civil infra; drop sports fields unless useful as texture negatives.

### Weak / missing from public sets (plan custom)

| Class | Public coverage | Action |
|-------|-----------------|--------|
| `landing_zone` | poor | label practice/edu frames + synthetic pads |
| `cargo` | poor | custom / logistics photos |
| `fire` | sparse in these four | add a dedicated fire/smoke set later if needed |
| `power_line` | partial (DOTA-like) | prefer dedicated PL datasets if AABB quality low |
| `forest` / `water` | partial via land-cover / DOTA-ish | may use semantic→boxes or skip until custom |

---

## 3. Recommended download packs (A100 job)

### Pack A — bootstrap (week 1)

1. VisDrone via Ultralytics (`yolo train data=VisDrone.yaml` once to fetch, or scripted download).  
2. UAVDT from DatasetNinja / official mirror → convert to YOLO.  
3. Remap labels → ids `{0,1}` only; train smoke **cerber-detect-A** (human+vehicle).

### Pack B — aerial structure (week 2)

1. DOTA (v1.0 or v1.5) detection split → OBB to YOLO AABB.  
2. Remap to `{1,5,6,7,11}` where confident.  
3. Merge with Pack A.

### Pack C — UAV awareness (week 2–3)

1. UETT4k-Anti-UAV from Hugging Face.  
2. Remap all positive UAV boxes → id `2`.  
3. Merge; balance with negatives from VisDrone empty sky crops if needed.

### Pack D — NULLXES custom (before flight weights freeze)

1. Edu airframe + SonicModell AR Wing Pro down/forward cams.  
2. Label: `landing_zone`, `obstacle`, `cargo`, hard cases for `power_line` / `human`.  
3. Mix ≥15–20% of final train epochs (fine-tune).

Layout on training host:

```
datasets/cerber/
  images/{train,val}/
  labels/{train,val}/
  data.yaml          # see cerber_data.yaml
  sources/           # raw VisDrone, UAVDT, DOTA, UETT4k (not shipped to aircraft)
```

---

## 4. `data.yaml` (train host)

File in repo as template: `cerber_data.yaml` (paths are host-local).

```yaml
# CERBER detect — YOLO (A100). Paths absolute on train machine.
path: /data/nullxes/datasets/cerber
train: images/train
val: images/val
names:
  0: human
  1: vehicle
  2: uav
  3: landing_zone
  4: obstacle
  5: power_line
  6: road
  7: building
  8: forest
  9: water
  10: fire
  11: infrastructure
  12: cargo
```

---

## 5. Machine bootstrap (RunPod / HF + Ultralytics)

**Pod (enough):** 1× RTX PRO 6000 **96 GB** · 140 GB RAM · 16 vCPU · **~2 TB** disk · image `runpod/pytorch:*-torch280-*` (Torch **already in image** — do not `pip install torch`).

Disk budget (rough): VisDrone ~4 GB extract · UAVDT+DOTA+UETT4k tens of GB · YOLO caches · runs/checkpoints — **under ~200 GB** typical; **2250 GB is fine**.

```bash
git clone https://github.com/MagistrTheOne/NULLXES-Black-Death.git
cd NULLXES-Black-Death

# extras only (no torch) — see models/requirements-train.txt
pip install -r 06_autonomy/models/requirements-train.txt

huggingface-cli login   # or export HF_TOKEN=...

python 06_autonomy/models/scripts/prepare_cerber_data.py \
  --root /workspace/datasets/cerber

# UAVDT / DOTA manual: sources/MANUAL_DOWNLOADS.md
# VisDrone: https://docs.ultralytics.com/datasets/detect/visdrone
# Train mode: https://docs.ultralytics.com/modes/train

python 06_autonomy/models/scripts/train_cerber_detect.py \
  --data /workspace/datasets/cerber/data.yaml

python 06_autonomy/models/scripts/train_cerber_detect.py \
  --data /workspace/datasets/cerber/data.yaml --export
```

| Source | How |
|--------|-----|
| VisDrone | Ultralytics `check_det_dataset("VisDrone.yaml")` auto zip (~2GB) → remap to CERBER ids |
| UETT4k | `huggingface_hub.snapshot_download("mugheessarwarawan/UETT4k-Anti-UAV")` |
| UAVDT / DOTA | DatasetNinja pages — manual YOLO convert into `images/` `labels/` |

Per [Ultralytics quickstart](https://docs.ultralytics.com/ru/quickstart). Recipe knobs: `configs/cerber_train.yaml`.

Notes for aerial / small objects (VisDrone lesson):

- Prefer **`imgsz=1280`** (or 960) over 640 for tiny targets; drop batch if OOM.  
- Start **`yolov8s`** or **`yolov8m`**; flight export may distill/`yolov8n` later if latency requires.  
- Flight decode: **YOLOv8 raw ONNX** (`yolo_v8_raw`). YOLO26 train OK if export stays compatible with that layout — verify tensor shape before freeze.

Export into repo:

```bash
python 06_autonomy/models/scripts/export_yolo_onnx.py \
  --weights /data/nullxes/runs/cerber-detect/v1/weights/best.pt \
  --imgsz 640 \
  --opset 17
```

Ship only `detector_alpha.onnx` + `sha256` + `classes:`. CERBER is the system; ONNX is one organ.

---

## 6. Remap cheat-sheet (source → CERBER detect id)

| Source class | → id |
|--------------|------|
| VisDrone pedestrian, people | 0 |
| VisDrone bicycle, car, van, truck, tricycle*, bus, motor | 1 |
| UAVDT car / bus / truck / … | 1 |
| DOTA plane | 2 (or drop if confused with fixed-wing self) |
| DOTA bridge, harbor, … | 11 |
| DOTA large-vehicle / small-vehicle | 1 |
| UETT4k UAV / drone | 2 |

\*tricycle/awning-tricycle: map to `vehicle` or drop.

---

## 7. Quality gates before calling weights “flight”

| Gate | Criterion |
|------|-----------|
| Val mAP50 | track per-class; human+vehicle+uav must not collapse |
| False UAV on self | check ego-prop overlays; suppress or hard-negatives |
| Export | `sha256` written; ORT session named I/O; layout `yolo_v8_raw` |
| Onboard | `imgsz` match letterbox config; conf/iou from yaml |

---

## 8. Name

| Name | Use |
|------|-----|
| **NULLXES CERBER** | perception **system** (product canon) |
| `cerber-detect` | Ultralytics runs / A100 job for the detect head |
| ONNX file | `detector_alpha.onnx` until Alpha freeze |
