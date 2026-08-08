"""Track-aware civil guidance — chase / escort / deny presence (ADR-004).

No munition bus. Outputs GoalMsg-compatible ENU target for simple_guidance.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from control.guidance.simple_guidance import NavState, SetpointOut, simple_guidance


@dataclass(frozen=True)
class TrackGuidanceConfig:
    chase_standoff_m: float = 8.0
    escort_offset_m: float = 15.0
    deny_radius_m: float = 25.0
    cruise_thrust: float = 0.35


def goal_from_track_mode(
    nav: NavState,
    target_x: float,
    target_y: float,
    target_z: float,
    mode: str,
    *,
    cfg: TrackGuidanceConfig | None = None,
) -> tuple[float, float, float]:
    """Map civil mode to a presence goal in ENU."""
    cfg = cfg or TrackGuidanceConfig()
    dx = target_x - nav.x
    dy = target_y - nav.y
    dist = math.hypot(dx, dy)
    if dist < 1e-3:
        return target_x, target_y, target_z

    ux, uy = dx / dist, dy / dist
    mode_l = mode.lower().strip()

    if mode_l == "chase":
        # Approach to standoff — do not occupy target point
        gx = target_x - ux * cfg.chase_standoff_m
        gy = target_y - uy * cfg.chase_standoff_m
        return gx, gy, target_z

    if mode_l == "escort":
        # Offset lateral to target
        gx = target_x - uy * cfg.escort_offset_m
        gy = target_y + ux * cfg.escort_offset_m
        return gx, gy, target_z

    if mode_l == "deny":
        # Hold outside deny radius facing target
        if dist < cfg.deny_radius_m:
            gx = target_x - ux * cfg.deny_radius_m
            gy = target_y - uy * cfg.deny_radius_m
            return gx, gy, target_z
        return nav.x, nav.y, nav.z

    # default: go toward target standoff
    return goal_from_track_mode(
        nav, target_x, target_y, target_z, "chase", cfg=cfg
    )


def track_guidance(
    nav: NavState,
    target_x: float,
    target_y: float,
    target_z: float,
    mode: str,
    *,
    cfg: TrackGuidanceConfig | None = None,
) -> SetpointOut:
    cfg = cfg or TrackGuidanceConfig()
    gx, gy, gz = goal_from_track_mode(
        nav, target_x, target_y, target_z, mode, cfg=cfg
    )
    return simple_guidance(nav, gx, gy, gz, cfg.cruise_thrust)
