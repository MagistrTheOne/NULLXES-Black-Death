"""Minimal state mirror payload (A ↔ B)."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class NavState:
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    vx: float = 0.0
    vy: float = 0.0
    vz: float = 0.0
    yaw: float = 0.0


@dataclass
class MirrorPacket:
    stamp_s: float
    channel_id: str
    active: bool
    mission_mode: str
    health_flags: dict[str, bool] = field(default_factory=dict)
    nav: NavState = field(default_factory=NavState)
    setpoint_hash: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MirrorPacket":
        nav_raw = data.get("nav") or {}
        nav = NavState(**{k: nav_raw.get(k, 0.0) for k in NavState.__dataclass_fields__})
        return cls(
            stamp_s=float(data["stamp_s"]),
            channel_id=str(data["channel_id"]),
            active=bool(data["active"]),
            mission_mode=str(data["mission_mode"]),
            health_flags=dict(data.get("health_flags") or {}),
            nav=nav,
            setpoint_hash=str(data.get("setpoint_hash") or ""),
        )
