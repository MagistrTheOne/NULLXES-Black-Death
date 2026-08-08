"""POSEIDON runtime — select packs, infer, remap to CERBER ids."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from perception.vision.decode import Detection
from perception.vision.infer_yolo import YoloDetector

from .merge import merge_detections
from .pack_spec import PackSpec, PackSpecError, load_pack_spec
from .router import PoseidonRouter, RouterConfig, RouterContext, load_router_config
from .session import build_specialist, remap_detections


@dataclass
class PackRunResult:
    pack_id: str
    latency_ms: float
    detections: list[Detection] = field(default_factory=list)
    error: str = ""


@dataclass
class PoseidonStepResult:
    specialist: list[Detection]
    pack_runs: list[PackRunResult]
    selected: list[str]


class PoseidonRuntime:
    def __init__(
        self,
        *,
        packs_root: Path,
        router_yaml: Path,
        pack_ids: list[str] | None = None,
    ) -> None:
        self.packs_root = Path(packs_root)
        self.specs: dict[str, PackSpec] = {}
        self.detectors: dict[str, YoloDetector] = {}
        ids = pack_ids or [
            p.name
            for p in sorted(self.packs_root.iterdir())
            if p.is_dir() and (p / "pack.yaml").is_file()
        ]
        for pack_id in ids:
            yaml_path = self.packs_root / pack_id / "pack.yaml"
            if not yaml_path.is_file():
                continue
            try:
                spec = load_pack_spec(yaml_path, verify_sha=True)
            except PackSpecError:
                continue
            self.specs[pack_id] = spec
            if spec.model_path.is_file() and spec.sha256:
                try:
                    self.detectors[pack_id] = build_specialist(spec)
                except Exception:
                    # Pack registered but not loadable — router skips at select if missing detector
                    pass

        router_cfg: RouterConfig = load_router_config(router_yaml)
        self.router = PoseidonRouter(router_cfg, list(self.specs.keys()))

    @property
    def loaded_pack_ids(self) -> list[str]:
        return sorted(self.detectors.keys())

    def step(self, bgr: np.ndarray, ctx: RouterContext) -> PoseidonStepResult:
        selected = [
            p for p in self.router.select(ctx) if p in self.detectors
        ]
        runs: list[PackRunResult] = []
        all_dets: list[Detection] = []
        for pack_id in selected:
            spec = self.specs[pack_id]
            det = self.detectors[pack_id]
            t0 = time.perf_counter()
            try:
                raw = det.infer(bgr)
                remapped = remap_detections(raw, spec.cerber_remap)
                ms = (time.perf_counter() - t0) * 1000.0
                runs.append(PackRunResult(pack_id, ms, remapped))
                all_dets.extend(remapped)
            except Exception as exc:  # noqa: BLE001
                ms = (time.perf_counter() - t0) * 1000.0
                runs.append(PackRunResult(pack_id, ms, [], error=str(exc)))
        return PoseidonStepResult(specialist=all_dets, pack_runs=runs, selected=selected)

    def merge_with_cerber(
        self,
        cerber: list[Detection],
        specialist: list[Detection],
        *,
        iou: float = 0.45,
    ) -> list[Detection]:
        return merge_detections(cerber, specialist, iou=iou)
