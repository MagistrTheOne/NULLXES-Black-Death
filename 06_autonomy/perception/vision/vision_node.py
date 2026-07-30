"""Vision pipeline — config → DetectorConfig → YoloDetector."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import yaml

from .infer_yolo import DetectorConfig, YoloDetector, build_detector
from .layout import LAYOUT_YOLO_V8_RAW
from .session_factory import OrtSessionFactory


class BlockedError(RuntimeError):
    pass


def load_detector_config(path: str | Path) -> dict[str, Any]:
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        raise BlockedError(f"BLOCKED: invalid detector config {path}")
    return data


def _require_str(cfg: dict[str, Any], key: str) -> str:
    if key not in cfg:
        raise BlockedError(f"BLOCKED: detector config missing '{key}'")
    val = str(cfg[key]).strip()
    if not val:
        raise BlockedError(f"BLOCKED: detector config '{key}' must be non-empty")
    return val


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def detector_config_from_yaml(cfg: dict[str, Any], repo_root: Path) -> DetectorConfig:
    if "num_classes" in cfg:
        raise BlockedError(
            "BLOCKED: do not set num_classes; use classes: list only "
            f"(got num_classes={cfg['num_classes']!r})"
        )

    raw_classes = cfg.get("classes")
    if not isinstance(raw_classes, list) or not raw_classes:
        raise BlockedError("BLOCKED: detector config 'classes' must be a non-empty list")
    classes = tuple(str(c) for c in raw_classes)

    layout = _require_str(cfg, "onnx_layout")
    if layout != LAYOUT_YOLO_V8_RAW:
        raise BlockedError(
            f"BLOCKED: onnx_layout must be {LAYOUT_YOLO_V8_RAW!r}, got {layout!r}"
        )

    model = repo_root / _require_str(cfg, "model_path")
    if not model.is_file():
        raise BlockedError(
            f"BLOCKED: missing ONNX {model}. "
            "Export real weights with models/scripts/export_yolo_onnx.py."
        )

    digest = _require_str(cfg, "sha256").lower()
    actual = _sha256_file(model)
    if actual != digest:
        raise BlockedError(
            f"BLOCKED: sha256 mismatch for {model}: "
            f"config={digest} file={actual}"
        )

    size = cfg.get("input_size")
    if not (isinstance(size, list) and len(size) == 2):
        raise BlockedError("BLOCKED: input_size must be [H, W]")

    providers_raw = cfg.get("providers")
    if not isinstance(providers_raw, list) or not providers_raw:
        raise BlockedError("BLOCKED: providers must be a non-empty list")
    providers = tuple(str(p) for p in providers_raw)

    for key in ("confidence", "iou", "input_name", "output_name"):
        if key not in cfg:
            raise BlockedError(f"BLOCKED: detector config missing '{key}'")

    return DetectorConfig(
        model_path=model,
        layout=layout,
        classes=classes,
        input_h=int(size[0]),
        input_w=int(size[1]),
        confidence=float(cfg["confidence"]),
        iou=float(cfg["iou"]),
        providers=providers,
        input_name=_require_str(cfg, "input_name"),
        output_name=_require_str(cfg, "output_name"),
        sha256=digest,
    )


class VisionPipeline:
    def __init__(
        self,
        config_path: str | Path,
        factory: OrtSessionFactory | None = None,
    ) -> None:
        cfg = load_detector_config(config_path)
        root = Path(__file__).resolve().parents[3]
        self._dcfg = detector_config_from_yaml(cfg, root)
        self.names = list(self._dcfg.classes)
        self.engine: YoloDetector = build_detector(self._dcfg, factory=factory)

    def process_bgr(self, frame_bgr: Any) -> list:
        return self.engine.infer(frame_bgr)

    def to_health(self, ok: bool, detail: str = "") -> dict[str, Any]:
        return {"vision_ok": ok, "detail": detail}
