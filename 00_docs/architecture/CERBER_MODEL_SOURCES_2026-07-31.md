# CERBER — open model sources (snapshot **2026-07-31**)

Specialized stack (preferred over one mega-detector). Class ids = `detector_alpha.yaml`  
(0 human … 12 cargo). Road/building/forest/water = **6–9**, not 3–6.

## Already ours

| Module | Artifact | Hub / path |
|--------|----------|------------|
| Detect v1 scene | yolov8s VisDrone | [MagistrTheOne/CERBER-CV](https://huggingface.co/MagistrTheOne/CERBER-CV) · local `weights/cerber-cv-v1` + `detector_alpha.onnx` |
| Detect v2 +UAV | FT Seraphim | [MagistrTheOne/CERBER-CV-v2](https://huggingface.co/MagistrTheOne/CERBER-CV-v2) · `detector_alpha_v2.onnx` |
| Collection | — | [nullxes-black-death-uav](https://huggingface.co/collections/MagistrTheOne/nullxes-black-death-uav-6a6c066b4f2f23d31e2a7d56) |

Flight runtime stays **ONNX Runtime** (AGPL Ultralytics train offline only).

---

## CERBER Detect — backbones & heads

| Source | What | Why for us | Link |
|--------|------|------------|------|
| **YOLO26** (Ultralytics, Jan 2026) | detect / seg / OBB / track; NMS-free E2E; STAL small objects | Next train generation (edge + aerial tiny targets); OBB for DOTA/power | [docs](https://docs.ultralytics.com/) · [v8.4 assets](https://github.com/ultralytics/assets/releases/tag/v8.4.0) · [arXiv](https://arxiv.org/html/2606.03748v1) · weights `yolo26n/s/m.pt` via `ultralytics` |
| **YOLO11** | prior SOTA family | Stable fallback if YOLO26 export/flight layout differs from `yolo_v8_raw` | [docs compare](https://docs.ultralytics.com/compare/yolo11-vs-yolo26) |
| **YOLOv8** | current CERBER-CV | Keep until YOLO26 ONNX layout validated in VisionPipeline | already used |
| **YOLOE-26** | open-vocab detect | Prototype rare classes (cargo) without full labels | Ultralytics YOLOE-26 |
| Fire / power FT bases | same YOLO* + FLAME / InsPLAD / MPID | Class heads 5,10,11 | datasets in [CERBER_DATASETS.md](./CERBER_DATASETS.md) |

**Flight note:** before switching backbone, lock `onnx_layout` + named I/O in `detector_alpha*.yaml`. YOLO26 NMS-free may need a new layout ADR.

---

## CERBER Segment — land cover (road / building / forest / water)

| Source | What | Link |
|--------|------|------|
| **SegFormer** (NVIDIA) | Transformer seg family; ImageNet / ADE20K pretrain | [NVlabs/SegFormer](https://github.com/NVlabs/SegFormer) · [MMSeg configs](https://github.com/open-mmlab/mmsegmentation) |
| **HF SegFormer landcover** | community LoveDA / landcover FT | e.g. [nave1616/SegFormer-landcover-FT](https://huggingface.co/nave1616/SegFormer-landcover-FT) (verify license/card) |
| **PrithviSeg / LoveDA pipelines** | LoveDA pretrain → drone orthophoto | [KyberNull/PrithviSeg](https://github.com/KyberNull/PrithviSeg) |
| **Ultralytics `*-seg`** | YOLO26/11/v8-seg | fast path if we want one vendor; weaker for pure land-cover than SegFormer |
| Data | LandCover.ai · LoveDA | see datasets doc |

Export target: ONNX semantic mask → CERBER Fusion (not necessarily Detect boxes).

---

## CERBER Track — association

| Source | Config / repo | Use |
|--------|---------------|-----|
| **BoT-SORT** (default Ultralytics) | `botsort.yaml` | UAV ego-motion + optional ReID — **first choice** for airframe |
| **ByteTrack** | `bytetrack.yaml` · [ifzhang/ByteTrack](https://github.com/ifzhang/ByteTrack) | lighter FPS |
| **OC-SORT / Deep OC-SORT / TrackTrack / FastTracker** | Ultralytics ≥8.4.63 trackers | crowded / non-linear / ReID |
| Docs | [Ultralytics Track](https://docs.ultralytics.com/modes/track) | `model.track(..., tracker="botsort.yaml")` |

Upstream papers/code still MIT for ByteTrack / BoT-SORT; use via Ultralytics for ONNX+IDs path.

---

## CERBER Navigation — landing / free space / obstacles

| Source | What | Link |
|--------|------|------|
| **OpenLander** | FOSS 3-class seg: obstacle / human / safe; ONNX | [stephansturges/OpenLander](https://github.com/stephansturges/OpenLander) · HF Space OpenLander ONNX |
| **VisLanding** (2025) | Metric3D V2 + SLZ seg; WildUAV | [arXiv:2506.14525](https://arxiv.org/abs/2506.14525) — check code release |
| **SafeLand** (2026) | Bayesian semantic landing map | [arXiv:2603.17430](https://arxiv.org/abs/2603.17430) · [project](https://markus-42.github.io/publications/2026/safeland/) — code “soon” as of Mar 2026 |
| **Metric3D V2** | depth/normals backbone for SLZ | used by VisLanding |
| Custom | landing_zone / cargo / obstacle | Stage 2 airframe capture |

OpenLander is the most deployable FOSS ONNX landing prior today; train CERBER Nav on own pad later.

---

## CERBER Fusion — decision layer

| Source | Role |
|--------|------|
| **In-repo DMI / fusion** | `06_autonomy/dmi/` · `perception/fusion/` EKF — not a Hub CV model |
| Detect+Seg+Track outputs | WorldFact / health / guidance contracts |
| Optional: Kalman / simple Bayesian fusion | no mandatory external “fusion net” for Alpha |

---

## Suggested adoption order (post v1-веха)

1. **Track** — BoT-SORT on CERBER-CV-v2 ONNX stream (zero new train).  
2. **Detect++** — YOLO26s FT for fire + power_line (FLAME + InsPLAD/MPID) → `CERBER-CV-v3` or side heads.  
3. **Segment** — SegFormer-B2 FT LoveDA/LandCover → ONNX masks for road/building/forest/water.  
4. **Nav** — trial OpenLander ONNX beside pad; then custom SLZ.  
5. **Fusion** — wire masks + tracks + boxes into DMI (already sketched).

## License watch

Ultralytics AGPL-3.0 (same as current train). OpenLander / ByteTrack / SegFormer — check each repo before commercial flight image. Internal NULLXES weights stay under project policy.
