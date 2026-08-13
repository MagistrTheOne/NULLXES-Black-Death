# CERBER V3 RunPod pack

**Canon:** `00_docs/architecture/CERBER_V3_ATLAS_RUNPOD.md`  
**Out:** `detector_alpha_v3.onnx` (does not overwrite v2b) then ATLAS-ALLOC on the same GPU.

```bash
export HF_TOKEN=hf_...
export CERBER_V3_ROOT=/workspace/datasets/cerber_v3
bash 06_autonomy/models/cerber_v3/scripts/runpod_v3_then_atlas.sh
```

Do not start the pod from this README. Maga starts the machine, then this script.
