"""ONNX Runtime session factory — named I/O only, no tensor-index guessing."""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path


def _ensure_cuda_dll_path() -> None:
    """Windows: expose torch/cuDNN CUDA 12 DLLs to ORT CUDA EP."""
    if sys.platform != "win32":
        return
    candidates: list[Path] = []
    try:
        import torch

        candidates.append(Path(torch.__file__).resolve().parent / "lib")
    except Exception:
        pass
    site = Path(sys.prefix) / "Lib" / "site-packages" / "nvidia"
    if site.is_dir():
        for sub in ("cublas", "cudnn", "cuda_runtime", "cufft", "curand", "cusolver", "cusparse"):
            bin_dir = site / sub / "bin"
            if bin_dir.is_dir():
                candidates.append(bin_dir)
    path = os.environ.get("PATH", "")
    parts = path.split(os.pathsep)
    for d in candidates:
        s = str(d)
        if d.is_dir() and s not in parts:
            parts.insert(0, s)
            try:
                os.add_dll_directory(s)
            except (OSError, AttributeError):
                pass
    os.environ["PATH"] = os.pathsep.join(parts)


@dataclass(frozen=True)
class OrtSession:
    """Thin wrapper: named I/O only."""

    _session: object
    input_name: str
    output_name: str

    def run(self, input_tensor: object) -> object:
        outs = self._session.run(
            [self.output_name],
            {self.input_name: input_tensor},
        )
        return outs[0]


class OrtSessionFactory:
    """Build ORT sessions with an explicit provider list from detector config."""

    def __init__(self, graph_optimization: bool = True) -> None:
        self.graph_optimization = graph_optimization

    def create(
        self,
        model_path: str | Path,
        *,
        providers: list[str],
        input_name: str,
        output_name: str,
    ) -> OrtSession:
        _ensure_cuda_dll_path()
        import onnxruntime as ort

        if not providers:
            raise RuntimeError("BLOCKED: providers must be non-empty")
        if not input_name or not output_name:
            raise RuntimeError("BLOCKED: input_name and output_name are required")

        opts = ort.SessionOptions()
        if self.graph_optimization:
            opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL

        available = set(ort.get_available_providers())
        selected = [p for p in providers if p in available]
        if not selected:
            raise RuntimeError(
                f"BLOCKED: none of providers {providers} available; "
                f"ORT has {sorted(available)}"
            )

        session = ort.InferenceSession(
            str(model_path),
            sess_options=opts,
            providers=selected,
        )
        in_names = {i.name for i in session.get_inputs()}
        out_names = {o.name for o in session.get_outputs()}
        if input_name not in in_names:
            raise RuntimeError(
                f"BLOCKED: input '{input_name}' not in {sorted(in_names)}"
            )
        if output_name not in out_names:
            raise RuntimeError(
                f"BLOCKED: output '{output_name}' not in {sorted(out_names)}"
            )

        return OrtSession(session, input_name, output_name)
