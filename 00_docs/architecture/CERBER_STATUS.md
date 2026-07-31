# NULLXES CERBER — Status

**Canon:** [CERBER.md](./CERBER.md) · **Metrics:** [CERBER_DETECT_METRICS_v1.md](./CERBER_DETECT_METRICS_v1.md) · **Datasets:** [CERBER_DATASETS.md](./CERBER_DATASETS.md)  
**Hub model:** [MagistrTheOne/CERBER-CV](https://huggingface.co/MagistrTheOne/CERBER-CV)

## Stage checklist

### Stage 1 — Detect v1 (VisDrone scene) — DONE 2026-07-31

- [x] Train host: RunPod RTX PRO 6000 + PyTorch 2.8 image (no torch in reqs)
- [x] VisDrone-DET via Ultralytics → CERBER remap (`human` / `vehicle`)
- [x] Train yolov8s · imgsz 1280 · batch 32 · 100 epochs (~2.015 h)
- [x] Val metrics locked (mAP50 **0.760** / mAP50-95 **0.439**)
- [x] Export ONNX imgsz 640 opset 17 → `detector_alpha.onnx`
- [x] PT vs ONNX smoke predict (same val image)
- [x] Publish HF: [CERBER-CV](https://huggingface.co/MagistrTheOne/CERBER-CV)
- [x] Local flight binaries: `detector_alpha.onnx` + `detector_alpha_v2.onnx` + v1/v2 `best.pt`
- [x] `detector_alpha.yaml` / `detector_alpha_v2.yaml` sha256 filled
- [x] HF Collection + CERBER-CV / CERBER-CV-v2
- [x] Seraphim UAV FT → v2
- [x] Metrics v1 + v2 docs

### Stage 2 — Onboard / airframe — START **2026-08-02**

- [ ] Copter arrives / bench power-on
- [ ] Camera → preprocess → CERBER ONNX → postprocess path on host (Windows/Linux)
- [ ] Load `detector_alpha.yaml` / `_v2` with verified sha256 (fail-closed)
- [ ] Live camera smoke: human/vehicle(/uav) boxes at conf 0.35
- [ ] Wire detections → DMI WorldFact / practice mission (civil only)
- [ ] Record short flight/bench log + failure modes (BLOCKED if no HW)

### August stack (Vision Stack canon — no YOLO26 flight swap yet)

See [CERBER_VISION_STACK.md](./CERBER_VISION_STACK.md).

- [ ] L3 Track: BoT-SORT on `detector_alpha_v2.onnx`
- [ ] L1 Detect++: FLAME (fire) + InsPLAD/MPID (power_line) → Hub revision
- [ ] L2 Segment: SegFormer service + LoveDA/LandCover
- [ ] L5 Fusion sketch: Detect+Seg+Track → DMI WorldFact
- [ ] YOLO26 offline A/B only (layout · FPS · export gate)

## What CERBER-CV is / is not

| Is | Is not |
|----|--------|
| Civil aerial **Detect** lane (v1 scene / v2 +UAV) | Full CERBER Vision Stack alone |
| Trained: human, vehicle (+ uav in v2) | Trained: landing_zone, fire, road seg, … |
| Flight path: ONNX Runtime | Cloud LLM / Ultralytics in flight |

## Artifacts

| Artifact | Location |
|----------|----------|
| Flight ONNX | `detector_alpha.onnx` (v1) · `detector_alpha_v2.onnx` (v2) |
| Flight config | `detector_alpha.yaml` · `detector_alpha_v2.yaml` |
| Hub | CERBER-CV · CERBER-CV-v2 · Collection |
