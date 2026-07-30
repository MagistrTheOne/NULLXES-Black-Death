"""EKF smoke test (requires filterpy)."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "06_autonomy"))

filterpy = pytest.importorskip("filterpy")

from perception.fusion.ekf_nav import NavEKF  # noqa: E402


def test_ekf_runs():
    ekf = NavEKF(dt=0.02)
    ekf.predict_imu(np.zeros(3))
    ekf.update_gnss(np.array([1.0, 2.0, 3.0]))
    assert ekf.state.shape == (6,)
