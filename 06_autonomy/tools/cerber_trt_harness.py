#!/usr/bin/env python3
"""CERBER TRT / ORT profiling harness — pin JetPack + nvpmodel before flight.

Usage (on Orin):
  python cerber_trt_harness.py --onnx path/to/cerber.onnx --frames 300
"""

from __future__ import annotations

import argparse
import json
import statistics
import time
from pathlib import Path


def _try_tegrastats_sample() -> dict:
    """Best-effort single tegrastats parse; empty on x86 host."""
    import shutil
    import subprocess

    if shutil.which("tegrastats") is None:
        return {"available": False}
    try:
        out = subprocess.check_output(
            ["tegrastats", "--interval", "1000"],
            timeout=2.5,
            stderr=subprocess.DEVNULL,
        )
        line = out.decode("utf-8", errors="replace").splitlines()[0]
        return {"available": True, "raw": line}
    except Exception as e:
        return {"available": False, "error": str(e)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--onnx", type=Path, required=True)
    ap.add_argument("--imgsz", type=int, default=640)
    ap.add_argument("--frames", type=int, default=100)
    ap.add_argument("--provider", default="auto", choices=["auto", "TensorrtExecutionProvider", "CUDAExecutionProvider", "CPUExecutionProvider"])
    args = ap.parse_args()

    if not args.onnx.is_file():
        print(json.dumps({"ok": False, "error": f"missing onnx {args.onnx}"}))
        return 2

    import numpy as np
    import onnxruntime as ort

    providers: list = []
    if args.provider == "auto":
        avail = ort.get_available_providers()
        for p in (
            "TensorrtExecutionProvider",
            "CUDAExecutionProvider",
            "CPUExecutionProvider",
        ):
            if p in avail:
                providers.append(p)
    else:
        providers = [args.provider]

    sess = ort.InferenceSession(str(args.onnx), providers=providers)
    inp = sess.get_inputs()[0]
    name = inp.name
    # NCHW float
    blob = np.random.rand(1, 3, args.imgsz, args.imgsz).astype(np.float32)
    # warmup
    for _ in range(5):
        sess.run(None, {name: blob})

    lat_ms: list[float] = []
    for _ in range(args.frames):
        t0 = time.perf_counter()
        sess.run(None, {name: blob})
        lat_ms.append((time.perf_counter() - t0) * 1000.0)

    lat_ms.sort()
    p95 = lat_ms[int(0.95 * (len(lat_ms) - 1))]
    report = {
        "ok": True,
        "onnx": str(args.onnx),
        "providers": sess.get_providers(),
        "frames": args.frames,
        "latency_ms_mean": statistics.mean(lat_ms),
        "latency_ms_p50": statistics.median(lat_ms),
        "latency_ms_p95": p95,
        "fps_mean": 1000.0 / max(1e-6, statistics.mean(lat_ms)),
        "acceptance_p95_le_40ms": p95 <= 40.0,
        "tegrastats": _try_tegrastats_sample(),
    }
    print(json.dumps(report, indent=2))
    return 0 if report["acceptance_p95_le_40ms"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
