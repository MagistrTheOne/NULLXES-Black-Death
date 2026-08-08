"""Track boxes + NavState → WorldFact (ground-plane pin v1)."""

from __future__ import annotations

import math
from dataclasses import dataclass

from dmi.messages import WorldFact
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
class CameraPinModel:
    """Pinhole forward cam stub — range from bbox height + assumed object height."""

    hfov_deg: float = 70.0
    image_w: float = 640.0
    image_h: float = 480.0
    # Assumed real height [m] by class for range estimate
    class_height_m: dict[int, float] | None = None

    def __post_init__(self) -> None:
        if self.class_height_m is None:
            object.__setattr__(
                self,
                "class_height_m",
                {
                    0: 1.7,  # human
                    1: 1.5,  # vehicle
                    2: 0.35,  # uav
                    5: 2.0,  # power_line span proxy
                    10: 2.0,  # fire plume proxy
                },
            )


def _bearing_range(
    track: Track,
    cam: CameraPinModel,
) -> tuple[float, float]:
    """Return (bearing_rad body-forward frame, range_m)."""
    cx = 0.5 * (track.x1 + track.x2)
    bh = max(1.0, track.y2 - track.y1)
    # bearing from optical axis
    nx = (cx / cam.image_w) - 0.5
    bearing = nx * math.radians(cam.hfov_deg)
    h_m = (cam.class_height_m or {}).get(track.cls_id, 1.0)
    # similar triangles: h_px / H_img ≈ h_m / (range * vfov_scale); use hfov proxy
    px_per_rad = cam.image_w / math.radians(cam.hfov_deg)
    range_m = max(1.0, (h_m * px_per_rad) / bh)
    return bearing, range_m


def track_to_enu(
    track: Track,
    nav: NavStateMsg,
    *,
    cam: CameraPinModel | None = None,
    source_id: str = "cerber",
    stamp_s: float | None = None,
) -> WorldFact:
    """Project track to ENU via ground-plane pin. BLOCKED accuracy without cal — v1 stub."""
    cam = cam or CameraPinModel()
    bearing, rng = _bearing_range(track, cam)
    yaw = nav.yaw
    # body forward +X when yaw=0 in ENU convention used by NavState
    dx = rng * math.cos(yaw + bearing)
    dy = rng * math.sin(yaw + bearing)
    x = nav.x + dx
    y = nav.y + dy
    z = nav.z
    kind = (
        CERBER_NAMES[track.cls_id]
        if 0 <= track.cls_id < len(CERBER_NAMES)
        else f"cls_{track.cls_id}"
    )
    return WorldFact(
        fact_id=f"trk-{track.track_id}",
        kind=kind,
        x=float(x),
        y=float(y),
        z=float(z),
        confidence=float(max(0.0, min(1.0, track.conf))),
        source_id=source_id,
        stamp_s=float(stamp_s if stamp_s is not None else nav.stamp_s),
    )


def tracks_to_facts(
    tracks: list[Track],
    nav: NavStateMsg | None,
    *,
    cam: CameraPinModel | None = None,
    source_id: str = "cerber",
    stamp_s: float = 0.0,
) -> list[WorldFact]:
    if nav is None:
        # No nav — publish image-space proxy as ENU offset zeros with low conf
        facts: list[WorldFact] = []
        for t in tracks:
            kind = (
                CERBER_NAMES[t.cls_id]
                if 0 <= t.cls_id < len(CERBER_NAMES)
                else f"cls_{t.cls_id}"
            )
            facts.append(
                WorldFact(
                    fact_id=f"trk-{t.track_id}",
                    kind=kind,
                    x=0.0,
                    y=0.0,
                    z=0.0,
                    confidence=float(max(0.0, min(0.3, t.conf * 0.5))),
                    source_id=source_id,
                    stamp_s=stamp_s,
                )
            )
        return facts
    return [
        track_to_enu(t, nav, cam=cam, source_id=source_id, stamp_s=stamp_s) for t in tracks
    ]
