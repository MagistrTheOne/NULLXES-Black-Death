"""Track boxes + NavState + calibration → WorldFact (ENU + covariance)."""

from __future__ import annotations

import math
from dataclasses import dataclass

from dmi.messages import WorldFact
from perception.calibration.models import CameraIntrinsics, Extrinsics
from perception.tracking.iou_tracker import Track
from soft_bus.messages import NavStateMsg

# CERBER locked names (detector_alpha.yaml order)
CERBER_NAMES: tuple[str, ...] = (
    "human",
    "vehicle",
    "uav",
    "landing_zone",
    "obstacle",
    "power_line",
    "road",
    "building",
    "forest",
    "water",
    "fire",
    "infrastructure",
    "cargo",
)


@dataclass(frozen=True)
class ObjectHeightPrior:
    class_height_m: dict[int, float]

    @staticmethod
    def default() -> ObjectHeightPrior:
        return ObjectHeightPrior(
            {
                0: 1.7,
                1: 1.5,
                2: 0.35,
                5: 2.0,
                10: 2.0,
            }
        )


@dataclass(frozen=True)
class FusionCalib:
    intrinsics: CameraIntrinsics
    T_body_cam: Extrinsics
    td_cam_imu_s: float = 0.0


def _kind(cls_id: int) -> str:
    if 0 <= cls_id < len(CERBER_NAMES):
        return CERBER_NAMES[cls_id]
    return f"cls_{cls_id}"


def _pixel_ray_cam(
    u: float,
    v: float,
    K: CameraIntrinsics,
) -> tuple[float, float, float]:
    """Unit ray in camera frame (OpenCV: +X right, +Y down, +Z forward)."""
    x = (u - K.cx) / K.fx
    y = (v - K.cy) / K.fy
    n = math.sqrt(x * x + y * y + 1.0)
    return x / n, y / n, 1.0 / n


def _yaw_rotate_body_to_enu(
    bx: float, by: float, bz: float, yaw: float
) -> tuple[float, float, float]:
    """Body +X forward, +Y left, +Z up → ENU with yaw from East toward North."""
    c, s = math.cos(yaw), math.sin(yaw)
    ex = c * bx - s * by
    ey = s * bx + c * by
    return ex, ey, bz


def _range_from_bbox_height(
    track: Track,
    K: CameraIntrinsics,
    prior: ObjectHeightPrior,
) -> tuple[float, float]:
    """Return (range_m, range_variance_m2) from pinhole similar triangles."""
    bh = max(1.0, track.y2 - track.y1)
    h_m = prior.class_height_m.get(track.cls_id, 1.0)
    range_m = max(1.0, (h_m * K.fy) / bh)
    # Rough: 20% range sigma + pixel uncertainty
    sig = max(0.5, 0.2 * range_m)
    return range_m, sig * sig


def track_to_enu(
    track: Track,
    nav: NavStateMsg,
    *,
    calib: FusionCalib | None = None,
    prior: ObjectHeightPrior | None = None,
    source_id: str = "cerber",
    stamp_s: float | None = None,
) -> WorldFact:
    """Project track to ENU using calibrated intrinsics + body↔cam extrinsics."""
    prior = prior or ObjectHeightPrior.default()
    stamp = float(stamp_s if stamp_s is not None else nav.stamp_s)
    kind = _kind(track.cls_id)
    stamp_ns = int(nav.stamp_ns or int(stamp * 1e9))
    sensor_ns = int(nav.sensor_stamp_ns or stamp_ns)

    if calib is None:
        # Fail-closed geometry: publish at vehicle with huge covariance.
        return WorldFact(
            fact_id=f"trk-{track.track_id}",
            kind=kind,
            x=float(nav.x),
            y=float(nav.y),
            z=float(nav.z),
            confidence=float(max(0.0, min(0.2, track.conf * 0.25))),
            source_id=source_id,
            stamp_s=stamp,
            frame_id="enu",
            cov_xx=1.0e6,
            cov_yy=1.0e6,
            cov_zz=1.0e6,
            stamp_ns=stamp_ns,
            sensor_stamp_ns=sensor_ns,
        )

    K = calib.intrinsics
    u = 0.5 * (track.x1 + track.x2)
    v = 0.5 * (track.y1 + track.y2)
    rx, ry, rz = _pixel_ray_cam(u, v, K)
    # Scale ray by range from bbox height prior
    range_m, range_var = _range_from_bbox_height(track, K, prior)
    p_cam = (rx * range_m, ry * range_m, rz * range_m)
    # Camera → body
    bx, by, bz = calib.T_body_cam.transform_point(p_cam[0], p_cam[1], p_cam[2])
    # Body → ENU via yaw (pitch/roll neglected v2; VIO/attitude full later)
    ex, ey, ez = _yaw_rotate_body_to_enu(bx, by, bz, nav.yaw)
    x = nav.x + ex
    y = nav.y + ey
    z = nav.z + ez

    # Covariance: range uncertainty along bearing + nav position cov
    bearing_sig = 0.05 * range_m
    cov_xy = range_var + bearing_sig * bearing_sig + float(nav.cov_xx)
    cov_z = range_var * 0.5 + float(nav.cov_zz)

    return WorldFact(
        fact_id=f"trk-{track.track_id}",
        kind=kind,
        x=float(x),
        y=float(y),
        z=float(z),
        confidence=float(max(0.0, min(1.0, track.conf))),
        source_id=source_id,
        stamp_s=stamp,
        frame_id="enu",
        cov_xx=float(cov_xy),
        cov_yy=float(cov_xy),
        cov_zz=float(cov_z),
        stamp_ns=stamp_ns,
        sensor_stamp_ns=sensor_ns,
    )


def tracks_to_facts(
    tracks: list[Track],
    nav: NavStateMsg | None,
    *,
    calib: FusionCalib | None = None,
    prior: ObjectHeightPrior | None = None,
    source_id: str = "cerber",
    stamp_s: float = 0.0,
) -> list[WorldFact]:
    if nav is None:
        facts: list[WorldFact] = []
        for t in tracks:
            facts.append(
                WorldFact(
                    fact_id=f"trk-{t.track_id}",
                    kind=_kind(t.cls_id),
                    x=0.0,
                    y=0.0,
                    z=0.0,
                    confidence=float(max(0.0, min(0.3, t.conf * 0.5))),
                    source_id=source_id,
                    stamp_s=stamp_s,
                    frame_id="enu",
                    cov_xx=1.0e6,
                    cov_yy=1.0e6,
                    cov_zz=1.0e6,
                )
            )
        return facts
    return [
        track_to_enu(
            t, nav, calib=calib, prior=prior, source_id=source_id, stamp_s=stamp_s
        )
        for t in tracks
    ]
