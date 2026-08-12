"""Local GSC TTS. ONNX NULLXES pack or SAPI. No cloud. No Qwen."""

from __future__ import annotations

from pathlib import Path

import yaml

TTS_PACK = (
    Path(__file__).resolve().parents[2] / "models" / "gsc" / "voice" / "nullxes_tts_v1" / "pack.yaml"
)
_FORBIDDEN = ("qwen", "llama", "gemini", "gpt", "ollama")


def pack_is_stable(pack_yaml: Path | None = None) -> bool:
    path = pack_yaml or TTS_PACK
    if not path.is_file():
        return False
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        return False
    name = str(raw.get("product_name", "")).lower()
    pid = str(raw.get("pack_id", "")).lower()
    if any(b in name or b in pid for b in _FORBIDDEN):
        return False
    if bool(raw.get("cloud_tts", False)):
        return False
    if str(raw.get("release_channel", "")).upper() != "STABLE":
        return False
    sha = str(raw.get("sha256", "pending")).lower()
    if sha in ("", "pending"):
        return False
    model = path.parent / str(raw.get("model_path", "model.onnx"))
    return model.is_file()


def backend_id(pack_yaml: Path | None = None) -> str:
    if pack_is_stable(pack_yaml):
        return "nullxes_onnx"
    return "sapi"


def load_onnx_session(pack_yaml: Path | None = None) -> object | None:
    path = pack_yaml or TTS_PACK
    if not pack_is_stable(path):
        return None
    import onnxruntime as ort

    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    model = path.parent / str(raw["model_path"])
    available = set(ort.get_available_providers())
    providers = [p for p in ("CUDAExecutionProvider", "CPUExecutionProvider") if p in available]
    return ort.InferenceSession(str(model), providers=providers or ["CPUExecutionProvider"])
