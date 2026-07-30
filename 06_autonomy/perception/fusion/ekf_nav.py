"""GNSS + IMU EKF (Alpha nav) — filterpy.

IMU contract (enforced by callers / drivers):
  accel_enu = linear acceleration in ENU [m/s^2], gravity already removed.
  Do not subtract g here.

Noise values below are Alpha prelim constants (not runtime guesses).
Recalibrate from Flight-1 logs before claiming flight-ready Q/R.
"""

from __future__ import annotations

import numpy as np
from filterpy.kalman import KalmanFilter

# Alpha prelim process / measurement noise (locked until Flight-1 calibration)
GNSS_POS_VAR_M2 = 2.5
PROCESS_POS_VAR = 0.5
PROCESS_VEL_VAR = 1.0
INIT_P_SCALE = 10.0
DEFAULT_DT_S = 0.02


def make_nav_ekf(dt: float = DEFAULT_DT_S) -> KalmanFilter:
    """State: [x, y, z, vx, vy, vz] ENU meters / m/s."""
    if dt <= 0.0:
        raise ValueError(f"dt must be > 0, got {dt}")
    kf = KalmanFilter(dim_x=6, dim_z=3)
    kf.x = np.zeros(6)
    kf.F = np.eye(6)
    for i in range(3):
        kf.F[i, i + 3] = dt
    kf.H = np.zeros((3, 6))
    kf.H[0, 0] = kf.H[1, 1] = kf.H[2, 2] = 1.0
    kf.P *= INIT_P_SCALE
    kf.R = np.eye(3) * GNSS_POS_VAR_M2
    kf.Q = np.eye(6)
    kf.Q[0:3, 0:3] *= PROCESS_POS_VAR
    kf.Q[3:6, 3:6] *= PROCESS_VEL_VAR
    return kf


class NavEKF:
    def __init__(self, dt: float = DEFAULT_DT_S) -> None:
        self.dt = dt
        self.kf = make_nav_ekf(dt)

    def predict_imu(self, accel_enu: np.ndarray) -> None:
        """Propagate with constant-velocity F, then apply linear accel to velocity."""
        a = np.asarray(accel_enu, dtype=float).reshape(3)
        self.kf.predict()
        self.kf.x[3:6] += a * self.dt

    def update_gnss(self, pos_enu: np.ndarray) -> None:
        self.kf.update(np.asarray(pos_enu, dtype=float).reshape(3))

    @property
    def state(self) -> np.ndarray:
        return self.kf.x.copy()
