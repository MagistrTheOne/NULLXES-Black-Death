# CERBER Detect — Datasets

**Status:** [CERBER_STATUS.md](./CERBER_STATUS.md) · stack: `06_autonomy/models/datasets/DATASET_STACK_A100.md`  
**Head nc=13:** human · vehicle · uav · landing_zone · obstacle · power_line · road · building · forest · water · fire · infrastructure · cargo

## Coverage now (trained)

| Class | id | Open data in stack | Notes |
|-------|----|--------------------|--------|
| human | 0 | VisDrone-DET | pedestrian/people |
| vehicle | 1 | VisDrone-DET | (+ UAVDT later) |
| uav | 2 | Seraphim (HF) · v2 FT | UETT4K full = SharePoint |

## Gap map → open sources (civil)

| Class | id | Priority | Candidate datasets | Format / catch |
|-------|----|----------|--------------------|----------------|
| **power_line** | 5 | **P0** | [InsPLAD](https://andreluizbvs.github.io/InsPLAD/) (~10.6k UAV assets) · [MPID](https://github.com/phd-benel/MPID) (insulators, YOLO) · HF [powerline-components-and-faults](https://huggingface.co/datasets/docmhvr/powerline-components-and-faults) | Map tower/insulator/conductor → `power_line` (+ optional `infrastructure`) |
| **building** | 7 | **P0** | [LandCover.ai](https://landcover.ai.linuxpolska.com/) · [LoveDA](https://github.com/Junjue-Wang/LoveDA) · [DOTA](https://captain-whu.github.io/DOTA/dataset) (weak) | LandCover/LoveDA = **seg** → need polygon→box or train seg lane later |
| **road** | 6 | **P0** | LandCover.ai · LoveDA | same seg→box |
| **forest** | 8 | **P0** | LandCover.ai (woodland) · LoveDA (forest) | same |
| **water** | 9 | **P0** | LandCover.ai · LoveDA · DOTA (swimming-pool/harbor weak) | same |
| **fire** | 10 | **P0** | [FLAME](https://ieee-dataport.org/open-access/flame-dataset-aerial-imagery-pile-burn-detection-using-drones-uavs) / [FLAME2](https://ieee-dataport.org/open-access/flame-2-fire-detection-and-modeling-aerial-multi-spectral-image-dataset) · YOLO boxes from FLAME masks ([Open MIND deriv.](https://doi.org/10.82432/10317/21516)) · FOTL_Drone (fire among FOD) | Prefer RGB box labels; IR optional later |
| **infrastructure** | 11 | **P1** | DOTA (bridge, harbor, storage-tank, airport…) · InsPLAD assets · xView | OBB→AABB for DOTA |
| **vehicle** (boost) | 1 | **P1** | [UAVDT](https://sites.google.com/view/grli-uavdt) · DOTA small/large-vehicle · VisDrone test-dev | Aerial traffic |
| **uav** (boost) | 2 | **P1** | Seraphim **train/** (~9GB zips) · [UETT4K](https://github.com/mugheessarwarawan/UETT4K-Anti-UAV) SharePoint · DOTA helicopter/plane (weak proxy) | Don’t map plane→uav blindly |
| **landing_zone** | 3 | **P2** | DOTA **helipad** / airport (v2) · **own pad photos** (Stage 2 airframe) | Open data thin; custom critical |
| **obstacle** | 4 | **P2** | Generic: poles/trees from InsPLAD · FOTL foreign objects · **custom flight hazards** | Vague class — define ontology (wire/tree/pole/…) |
| **cargo** | 12 | **P2** | Almost none clean open aerial package-drop sets · **custom** (box/parachute/payload) | Plan capture on practice flights |
| human (boost) | 0 | **P2** | VisDrone VID frames · crowd subsets | Optional denser people |

## Recommended Stage-3 stacks (hypotheses)

### A — Scene fill (road/building/forest/water) — highest leverage for “13 metrics”

1. **LandCover.ai** — building / woodland→forest / water / road ([site](https://landcover.ai.linuxpolska.com/))  
2. **LoveDA** — building / road / water / forest ([Zenodo](https://doi.org/10.5281/zenodo.5706578))  
3. Pipeline: tile → mask connected components → axis boxes → CERBER ids 6–9  

*Or* keep these as **CERBER Segmentation** lane and only promote stable blobs to detect boxes.

### B — Power / civil infra

1. **InsPLAD-det** — power assets from real UAV inspection  
2. **MPID** — YOLO insulators ready  
3. Remap → `power_line` (+ coarse `infrastructure`)

### C — Fire

1. **FLAME** (+ YOLO conversion if using masks)  
2. Keep civil wildfire / pile-burn only (already fits product)

### D — Aerial objects / UAV / vehicles

1. VisDrone + Seraphim (done)  
2. UAVDT + DOTA AABB for vehicles / bridges  
3. UETT4K when SharePoint available  

### E — Must capture yourself

| Class | Why open data fails |
|-------|---------------------|
| landing_zone | Pad markings / grass strips are mission-specific |
| cargo | Delivery payload / drop bags not in public DET sets |
| obstacle | Needs your threat model (wires, towers, trees…) |

## Already used

| Dataset | Role | Source |
|---------|------|--------|
| VisDrone-DET | human, vehicle | [VisDrone-Dataset](https://github.com/VisDrone/VisDrone-Dataset) · Ultralytics |
| Seraphim drone YOLO | uav | [HF](https://huggingface.co/datasets/lgrzybowski/seraphim-drone-detection-dataset) (`test/` zips → v2) |

## Stage 2+ — UAV class boost («ночной кошмар» = detector)

**Product idea:** CERBER = глаза **оборонного перехватчика-преследователя** (без вооружённого стека):  
Detect/Track чужой БПЛА → guidance chase / escort / airspace deny presence.  
Силуэты consumer / FPV / large / military-looking = один класс `uav=2`.  
**Не оружие.** Нет fire-control / munitions datasets.

### Ranked data sources (HF search 2026-08-04 + open benchmarks)

| Rank | Dataset | Where | Why | License / catch |
|------|---------|-------|-----|-----------------|
| **1** | **Seraphim** (уже в v2) | HF [`lgrzybowski/seraphim-drone-detection-dataset`](https://huggingface.co/datasets/lgrzybowski/seraphim-drone-detection-dataset) | YOLO zips, CC-BY-4.0, скрипт merge готов | `--full` ~9GB train; v2 юзал test/ |
| **2** | **DUT Anti-UAV** | [GitHub](https://github.com/wangdongdut/DUT-Anti-UAV) · GDrive/Baidu | ~10k RGB DET, 35 моделей дронов, day/night/weather, tiny targets | MIT; **не на HF** — качать GDrive |
| **3** | **UETT4K Anti-UAV** | [GitHub](https://github.com/mugheessarwarawan/UETT4K-Anti-UAV) → SharePoint | ~33k; крупный anti-UAV dump | **Не на HF** (404). SharePoint only — см. `prepare_cerber_data.py` |
| **4** | **Anti-UAV / Anti-UAV410** (RGB-T) | Challenge + HF mirrors e.g. [`CornBac0n/Anti-UAV-RGBT`](https://huggingface.co/datasets/CornBac0n/Anti-UAV-RGBT) | IR+RGB, ночь («кошмар» в темноте) | Часто tracking boxes; remap → DET; IR = отдельный EP позже |
| **5** | Drone-vs-Bird | AVSS / challenge dumps | long-range + bird hard-negatives | Снижает FP «птица=дрон» |
| **6** | Det-Fly | papers / author release | ego / air-to-air angles | Доп. домен после DUT |
| — | HF small YOLO packs (`pathikg/…`, `Heelii1111/…`) | HF | Быстрый долив | Проверять дубли/качество; не база |
| **REJECT** | Battle-tank / weapon / fire-control sets | e.g. tank DET на HF | Ломает civil constraint | Не мешать в CERBER |

Open Images V7 — **не** для `uav`; это CERBER RT (chair/table/person), другой трек.

### Как качать

```bash
# Seraphim (HF) — уже автоматизировано
python 06_autonomy/models/scripts/merge_uav_seraphim.py --root /data/cerber --full

# или snapshot
huggingface-cli download lgrzybowski/seraphim-drone-detection-dataset --repo-type dataset --local-dir ./sources/seraphim

# DUT Anti-UAV — с GitHub README (Google Drive train/val/test)
# → положить в sources/dut_anti_uav/{train,val,test}
# → конверт в YOLO txt, class_id := 2

# UETT4K — SharePoint link из GitHub README (не HF)
python 06_autonomy/models/scripts/prepare_cerber_data.py   # печатает URL / note
```

### Как учим (пайплайн NULLXES)

```
base: CERBER-CV / v2 best.pt
  + mix: VisDrone(human,vehicle) + Seraphim+DUT(+UETT4K) → class uav=2 only
  → Ultralytics train (offline GPU) imgsz 1280 preferred for tiny UAV
  → export ONNX opset 17 → detector_alpha_v3.onnx (не затирать v1/v2)
  → sha256 в detector_alpha_v3.yaml
  → runtime: ORT only
```

| Knob | Stage-2 UAV boost |
|------|-------------------|
| Init | `CERBER-CV-v2` best.pt |
| Mix ratio | keep VisDrone so human/vehicle не умирают (v2 уже просел) |
| imgsz | **1280** train / export flight 640 или dual |
| Epochs | 40–80 FT |
| Hard neg | birds / empty sky slices |
| Track next | BoT-SORT on `uav` stream → WorldFact |

### Product framing (ночной кошмар)

| Is | Is not |
|----|--------|
| Sense other UAVs in FOV | Kinetic intercept / weapons |
| Alert / avoid / DMI WorldFact `kind=uav` | Fire-control lock |
| Day RGB now · IR later (Anti-UAV410) | Combat mission labels |
| Civil airspace + infra safety | Targeting datasets |

## Remap

`06_autonomy/models/datasets/remap_rules.yaml` · `scripts/prepare_cerber_data.py` · `scripts/merge_uav_seraphim.py`

## Civil constraint

Civil infrastructure / public aerial / wildfire safety / **airspace awareness (other UAV as traffic)**.  
No weapons, targeting, or fire-control datasets.

## Practical order to “close” 13 classes

| Wave | Classes closed | Data |
|------|----------------|------|
| Done | 0,1 (+2 in v2) | VisDrone + Seraphim |
| Next pod (~1–2 days) | 5,10,11 | InsPLAD/MPID + FLAME(+YOLO) + DOTA subset |
| Next (+seg tooling) | 6,7,8,9 | LandCover.ai / LoveDA → boxes |
| Airframe Stage 2+ | 3,4,12 | Custom flights |
