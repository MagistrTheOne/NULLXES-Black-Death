# ONNX weights — production only

| File | Role | Config |
|------|------|--------|
| `detector_alpha.onnx` | CERBER-CV **v1** scene (VisDrone human/vehicle) | `configs/detector_alpha.yaml` |
| `detector_alpha_v2.onnx` | CERBER-CV **v2** +UAV FT | `configs/detector_alpha_v2.yaml` |
| `detector_alpha_v2b.onnx` | CERBER-CV **v2b** pursuit boost (RunPod pack) | `configs/detector_alpha_v2b.yaml` · pack `cerber_v2/` |
| `detector_alpha_v3.onnx` | CERBER-CV **v3** +power_line FT (does not overwrite v2b) | `configs/detector_alpha_v3.yaml` · pack `cerber_v3/` |

Layout: **yolo_v8_raw** `[1, 4+nc, N]`. Weights gitignored (`*.onnx`); keep sha256 in yaml.  
Hub: [CERBER-CV](https://huggingface.co/MagistrTheOne/CERBER-CV) · [CERBER-CV-v2](https://huggingface.co/MagistrTheOne/CERBER-CV-v2)

Perception system: **NULLXES CERBER** (`00_docs/architecture/CERBER.md`).  
Detect train stack: `../datasets/DATASET_STACK_A100.md` (`cerber-detect` runs).
