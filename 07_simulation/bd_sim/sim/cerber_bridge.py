"""CERBER ZMQ bridge — fail-closed. No fake boxes. Optional worker."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
STUDIO = ROOT.parent / "cerber_studio"
if str(STUDIO) not in sys.path:
    sys.path.insert(0, str(STUDIO))

FRAME_EP = "tcp://127.0.0.1:5593"
RESULT_EP = "tcp://127.0.0.1:5594"


class CerberBridge:
    def __init__(self) -> None:
        self.enabled = False
        self.detail = "CERBER off (pass --cerber)"
        self.tracks: list[dict[str, Any]] = []
        self.has_track = False
        self._pub = None
        self._sub = None

    def start(self) -> None:
        try:
            from studio.ipc import FramePublisher, ResultSubscriber
        except Exception as exc:  # noqa: BLE001
            self.detail = f"BLOCKED: {exc}"
            self.enabled = False
            return
        self._pub = FramePublisher(FRAME_EP)
        self._sub = ResultSubscriber(RESULT_EP)
        self.enabled = True
        self.detail = f"PUB {FRAME_EP} — start studio worker --frames {FRAME_EP} --results {RESULT_EP}"

    def send_frame(self, bgr: np.ndarray) -> None:
        if not self.enabled or self._pub is None:
            return
        try:
            self._pub.send(bgr, meta={"src": "bd_sim"})
        except Exception as exc:  # noqa: BLE001
            self.detail = f"BLOCKED: {exc}"
            self.enabled = False

    def poll(self) -> None:
        if not self.enabled or self._sub is None:
            self.has_track = False
            return
        try:
            res = self._sub.recv()
        except Exception:  # noqa: BLE001
            return
        if res is None:
            return
        self.tracks = [
            {"id": t.track_id, "name": t.name, "conf": t.conf} for t in res.tracks
        ]
        self.has_track = any(t.name in ("uav", "human", "vehicle") or t.cls_id == 2 for t in res.tracks)
        if not res.health.vision_ok:
            self.detail = res.health.detail or "BLOCKED"
            self.has_track = False
        else:
            self.detail = f"ok fps={res.health.infer_fps:.1f} tracks={len(res.tracks)}"

    def close(self) -> None:
        if self._pub is not None:
            self._pub.close()
        if self._sub is not None:
            self._sub.close()
