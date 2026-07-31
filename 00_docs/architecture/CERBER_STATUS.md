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
- [ ] Sync `detector_alpha.onnx` + sha256 into local/git flight tree
- [ ] HF Collection **NULLXES BLACK DEATH (UAV)** + add CERBER-CV
- [x] Optional leftover-pod: Seraphim `test/` → class `uav` + short FT (`v1-uav-ft`)
- [ ] Export + publish **CERBER-CV-v2** (separate Hub repo, same Collection)
- [ ] See [CERBER_DETECT_METRICS_v2.md](./CERBER_DETECT_METRICS_v2.md)

### Stage 2 — Onboard / airframe — START **2026-08-02**

- [ ] Copter arrives / bench power-on
- [ ] Camera → preprocess → CERBER ONNX → postprocess path on host (Windows/Linux)
- [ ] Load `detector_alpha.yaml` with verified sha256 (fail-closed)
- [ ] Live camera smoke: human/vehicle boxes at conf 0.35
- [ ] Wire detections → DMI WorldFact / practice mission (civil only)
- [ ] Record short flight/bench log + failure modes (BLOCKED if no HW)
- [ ] Plan Stage 3 data: UAV / landing_zone / custom (empty classes today)

## What CERBER-CV v1 is / is not

| Is | Is not |
|----|--------|
| Civil aerial **scene** detector | Full UAV intelligence |
| Trained: human + vehicle | Trained: uav, landing_zone, fire, … |
| Flight path: ONNX Runtime | Cloud LLM / Ultralytics in flight |

## Artifacts

| Artifact | Location |
|----------|----------|
| Hub | `MagistrTheOne/CERBER-CV` |
| Train run | `runs/detect/cerber-detect/v1/` (pod) |
| Flight ONNX | `06_autonomy/models/onnx/detector_alpha.onnx` |
| Flight config | `06_autonomy/models/configs/detector_alpha.yaml` |
