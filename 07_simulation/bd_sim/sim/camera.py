"""Latency ring for Camera S1. Grab is done by the engine."""

from __future__ import annotations

from collections import deque

import numpy as np


class LatencyCam:
    def __init__(self, delay_frames: int = 2) -> None:
        self.buf: deque[np.ndarray] = deque(maxlen=max(1, delay_frames + 1))
        self.delay_frames = max(0, delay_frames)

    def push(self, rgb: np.ndarray) -> np.ndarray:
        self.buf.append(rgb.copy())
        if len(self.buf) <= self.delay_frames:
            return rgb
        return self.buf[0]
