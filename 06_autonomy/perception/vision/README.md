# Vision perception

## Pipeline

```
BGR frame
 → letterbox + NCHW
 → OrtSessionFactory → named input/output (from config)
 → decode YOLO_V8_RAW [1, 4+nc, N]  (strict)
 → class-aware NMS (iou from config)
 → Detection[]
```

## Config

`models/configs/detector_alpha.yaml` — required fields:
- `onnx_layout: yolo_v8_raw`
- `classes:` → `num_classes = len(classes)` (do not set `num_classes`)
- `input_name` / `output_name` (must match ONNX graph)
- `confidence` / `iou` / `providers`
- `sha256` — must match the ONNX file bytes (verified at load)

## BLOCKED without

Real `detector_alpha.onnx` + non-empty matching `sha256` + camera frames on the bus.
No alternate layout, transpose guess, or dummy weights.
