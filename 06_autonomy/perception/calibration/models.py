"""Calibration models — intrinsics / extrinsics / time offset."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CameraIntrinsics:
    width: int
    height: int
    fx: float
    fy: float
    cx: float
    cy: float
    # Brown-Conrady: k1,k2,p1,p2,k3
    dist: tuple[float, ...] = (0.0, 0.0, 0.0, 0.0, 0.0)
    camera_name: str = "forward"


@dataclass(frozen=True)
class Extrinsics:
    """Homogeneous transform: point_parent = R * point_child + t."""

    # row-major 3x3
    R: tuple[float, ...]
    t: tuple[float, float, float]
    parent_frame: str
    child_frame: str

    def transform_point(self, x: float, y: float, z: float) -> tuple[float, float, float]:
        r = self.R
        px = r[0] * x + r[1] * y + r[2] * z + self.t[0]
        py = r[3] * x + r[4] * y + r[5] * z + self.t[1]
        pz = r[6] * x + r[7] * y + r[8] * z + self.t[2]
        return px, py, pz
