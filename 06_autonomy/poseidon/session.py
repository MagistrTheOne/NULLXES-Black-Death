"""POSEIDON specialist ORT session — yolo_v8_raw only."""

from __future__ import annotations

from perception.vision.decode import Detection
from perception.vision.infer_yolo import DetectorConfig, YoloDetector
from perception.vision.nms import nms
from perception.vision.session_factory import OrtSessionFactory

from .pack_spec import PackSpec, PackSpecError


def build_specialist(spec: PackSpec, factory: OrtSessionFactory | None = None) -> YoloDetector:
    if not spec.model_path.is_file():
        raise PackSpecError(f"BLOCKED: pack {spec.pack_id} has no ONNX at {spec.model_path}")
    cfg = DetectorConfig(
        model_path=spec.model_path,
        layout=spec.onnx_layout,
        classes=spec.classes,
        input_h=spec.input_h,
        input_w=spec.input_w,
        confidence=spec.confidence,
        iou=spec.iou,
        providers=spec.providers,
        input_name=spec.input_name,
        output_name=spec.output_name,
        sha256=spec.sha256 or "pending",
    )
    return YoloDetector(
        cfg,
        (factory or OrtSessionFactory()).create(
            cfg.model_path,
            providers=list(cfg.providers),
            input_name=cfg.input_name,
            output_name=cfg.output_name,
        ),
    )


def remap_detections(dets: list[Detection], remap: dict[int, int]) -> list[Detection]:
    out: list[Detection] = []
    for d in dets:
        if d.cls_id not in remap:
            continue
        out.append(
            Detection(
                cls_id=int(remap[d.cls_id]),
                conf=d.conf,
                x1=d.x1,
                y1=d.y1,
                x2=d.x2,
                y2=d.y2,
            )
        )
    return out


def class_aware_nms(dets: list[Detection], iou: float) -> list[Detection]:
    return nms(dets, iou)
