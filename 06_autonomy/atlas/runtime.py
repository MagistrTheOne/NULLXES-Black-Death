"""Fail-closed ATLAS pack load — CANDIDATE/pending sha never used as STABLE."""

from __future__ import annotations

from pathlib import Path

import yaml


def pack_is_stable(pack_yaml: Path) -> bool:
    if not pack_yaml.is_file():
        return False
    raw = yaml.safe_load(pack_yaml.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        return False
    if str(raw.get("release_channel", "")).upper() != "STABLE":
        return False
    sha = str(raw.get("sha256", "pending")).lower()
    if sha in ("", "pending"):
        return False
    model = pack_yaml.parent / str(raw.get("model_path", "model.onnx"))
    return model.is_file()


def load_onnx_session(pack_yaml: Path) -> object | None:
    if not pack_is_stable(pack_yaml):
        return None
    import onnxruntime as ort

    raw = yaml.safe_load(pack_yaml.read_text(encoding="utf-8"))
    model = pack_yaml.parent / str(raw["model_path"])
    available = set(ort.get_available_providers())
    providers = [p for p in ("CUDAExecutionProvider", "CPUExecutionProvider") if p in available]
    return ort.InferenceSession(str(model), providers=providers or ["CPUExecutionProvider"])
