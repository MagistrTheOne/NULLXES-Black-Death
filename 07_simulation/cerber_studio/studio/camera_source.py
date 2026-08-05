"""Virtual nose-camera sampling helpers."""

from __future__ import annotations

import numpy as np

from .viewport import StudioEngine


def read_nose_bgr(engine: StudioEngine) -> np.ndarray:
    return engine.sample_cerber_bgr()
