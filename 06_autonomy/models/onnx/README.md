# ONNX weights — production only

| File | Role |
|------|------|
| `detector_alpha.onnx` | flight weights — **required**; produce via `scripts/export_yolo_onnx.py --weights <real.pt>` |

Layout: **yolo_v8_raw** `[1, 4+nc, N]` — `configs/detector_alpha.yaml`.

**BLOCKED** until a real trained `.pt` is exported. No dummy/placeholder weights in this repo.

Perception system: **NULLXES CERBER** (`00_docs/architecture/CERBER.md`).  
Detect train stack: `../datasets/DATASET_STACK_A100.md` (`cerber-detect` runs).
