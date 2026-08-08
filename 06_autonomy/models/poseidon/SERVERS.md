# NULLXES servers — CERBER / POSEIDON

No Ollama. No public LLM APIs in the mission path.

| Role | Job |
|------|-----|
| Train farm | Ultralytics FT per pack + CERBER v2/v2b on RTX PRO 6000 / cluster |
| Export | `poseidon/scripts/export_pack.py` → `model.onnx` + sha256 |
| Registry | `registry/registry.yaml` + pack.yaml fail-closed |
| GSC | `dmi/coordinator.py` / `ros2/nodes/dmi_coordinator_soft.py` |
| CI | `python models/poseidon/scripts/validate_registry.py` + unit tests |

Companion loads only packs with real sha + ONNX. Pending manifests are registry placeholders.
