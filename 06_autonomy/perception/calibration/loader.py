"""Load calibration YAML bundle + content hashes for SoftBus."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

import yaml

from .models import CameraIntrinsics, Extrinsics


@dataclass(frozen=True)
class CalibBundle:
    camera: CameraIntrinsics
    T_body_cam: Extrinsics
    T_body_imu: Extrinsics
    td_cam_imu_s: float
    camera_hash: str
    imu_hash: str
    extrinsics_hash: str

    @property
    def ok(self) -> bool:
        return bool(self.camera_hash and self.extrinsics_hash)


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def _load_extrinsics(raw: dict, *, default_parent: str, default_child: str) -> Extrinsics:
    R = raw.get("R")
    if R is None:
        R = [1, 0, 0, 0, 1, 0, 0, 0, 1]
    flat = tuple(float(x) for x in R)
    if len(flat) != 9:
        raise ValueError("extrinsics R must be 9 floats row-major")
    t_raw = raw.get("t", [0.0, 0.0, 0.0])
    t = (float(t_raw[0]), float(t_raw[1]), float(t_raw[2]))
    return Extrinsics(
        R=flat,
        t=t,
        parent_frame=str(raw.get("parent_frame", default_parent)),
        child_frame=str(raw.get("child_frame", default_child)),
    )


def load_calib_bundle(
    camera_yaml: Path,
    extrinsics_yaml: Path,
    imu_yaml: Path | None = None,
) -> CalibBundle:
    cam_raw = yaml.safe_load(camera_yaml.read_text(encoding="utf-8"))
    ext_raw = yaml.safe_load(extrinsics_yaml.read_text(encoding="utf-8"))
    imu_hash = _sha256_file(imu_yaml) if imu_yaml and imu_yaml.is_file() else ""

    intr = cam_raw["intrinsics"]
    dist = tuple(float(x) for x in intr.get("dist", [0, 0, 0, 0, 0]))
    camera = CameraIntrinsics(
        width=int(intr["width"]),
        height=int(intr["height"]),
        fx=float(intr["fx"]),
        fy=float(intr["fy"]),
        cx=float(intr["cx"]),
        cy=float(intr["cy"]),
        dist=dist,
        camera_name=str(cam_raw.get("camera_name", "forward")),
    )
    T_body_cam = _load_extrinsics(
        ext_raw.get("T_body_cam", {}),
        default_parent="body",
        default_child="cam_forward",
    )
    T_body_imu = _load_extrinsics(
        ext_raw.get("T_body_imu", {"R": [1, 0, 0, 0, 1, 0, 0, 0, 1], "t": [0, 0, 0]}),
        default_parent="body",
        default_child="imu0",
    )
    td = float(ext_raw.get("td_cam_imu_s", 0.0))
    return CalibBundle(
        camera=camera,
        T_body_cam=T_body_cam,
        T_body_imu=T_body_imu,
        td_cam_imu_s=td,
        camera_hash=_sha256_file(camera_yaml),
        imu_hash=imu_hash,
        extrinsics_hash=_sha256_file(extrinsics_yaml),
    )
