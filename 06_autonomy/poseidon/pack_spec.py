"""POSEIDON pack.yaml load + sha256 fail-closed."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


class PackSpecError(RuntimeError):
    pass


@dataclass(frozen=True)
class PackSpec:
    pack_id: str
    dataset: str
    onnx_layout: str
    model_path: Path
    sha256: str
    input_h: int
    input_w: int
    classes: tuple[str, ...]
    cerber_remap: dict[int, int]
    confidence: float
    iou: float
    providers: tuple[str, ...]
    budget_ms: float
    input_name: str
    output_name: str
    required: bool


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_pack_spec(pack_yaml: str | Path, *, verify_sha: bool = True) -> PackSpec:
    path = Path(pack_yaml).resolve()
    if not path.is_file():
        raise PackSpecError(f"BLOCKED: missing pack.yaml {path}")
    with open(path, encoding="utf-8") as f:
        raw: Any = yaml.safe_load(f)
    if not isinstance(raw, dict):
        raise PackSpecError(f"BLOCKED: invalid pack.yaml {path}")

    pack_dir = path.parent
    pack_id = str(raw.get("pack_id", "")).strip()
    if not pack_id:
        raise PackSpecError("BLOCKED: pack_id required")

    layout = str(raw.get("onnx_layout", "yolo_v8_raw")).strip()
    if layout != "yolo_v8_raw":
        raise PackSpecError(f"BLOCKED: unsupported onnx_layout={layout!r}")

    model_rel = str(raw.get("model_path", "model.onnx")).strip()
    model_path = (pack_dir / model_rel).resolve()
    digest = str(raw.get("sha256", "")).strip().lower()
    placeholder = digest in ("", "<filled_on_export>", "pending", "todo")

    if not model_path.is_file():
        if raw.get("required", False):
            raise PackSpecError(f"BLOCKED: missing ONNX {model_path}")
        # Allow manifest-only packs until export fills weights.
        if not placeholder:
            raise PackSpecError(f"BLOCKED: missing ONNX {model_path}")
    elif verify_sha and not placeholder:
        actual = _sha256_file(model_path)
        if actual != digest:
            raise PackSpecError(
                f"BLOCKED: sha256 mismatch pack={pack_id} config={digest} file={actual}"
            )

    size = raw.get("input_size")
    if not (isinstance(size, list) and len(size) == 2):
        raise PackSpecError("BLOCKED: input_size must be [H, W]")

    classes_raw = raw.get("classes")
    if not isinstance(classes_raw, list) or not classes_raw:
        raise PackSpecError("BLOCKED: classes must be non-empty list")

    remap_raw = raw.get("cerber_remap")
    if not isinstance(remap_raw, dict) or not remap_raw:
        raise PackSpecError("BLOCKED: cerber_remap required")
    cerber_remap = {int(k): int(v) for k, v in remap_raw.items()}

    providers_raw = raw.get("providers") or ["CUDAExecutionProvider", "CPUExecutionProvider"]
    if not isinstance(providers_raw, list) or not providers_raw:
        raise PackSpecError("BLOCKED: providers must be non-empty list")

    return PackSpec(
        pack_id=pack_id,
        dataset=str(raw.get("dataset", "")).strip(),
        onnx_layout=layout,
        model_path=model_path,
        sha256=digest if not placeholder else "",
        input_h=int(size[0]),
        input_w=int(size[1]),
        classes=tuple(str(c) for c in classes_raw),
        cerber_remap=cerber_remap,
        confidence=float(raw.get("confidence", 0.35)),
        iou=float(raw.get("iou", 0.45)),
        providers=tuple(str(p) for p in providers_raw),
        budget_ms=float(raw.get("budget_ms", 12.0)),
        input_name=str(raw.get("input_name", "images")).strip(),
        output_name=str(raw.get("output_name", "output0")).strip(),
        required=bool(raw.get("required", False)),
    )
