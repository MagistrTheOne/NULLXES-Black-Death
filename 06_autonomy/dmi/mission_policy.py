"""Runtime MissionProfile gate (MISSION_POLICY_SPEC)."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from soft_bus.messages import PolicyDecisionMsg


@dataclass(frozen=True)
class Geofence:
    xmin: float = -1.0e9
    xmax: float = 1.0e9
    ymin: float = -1.0e9
    ymax: float = 1.0e9
    zmin: float = -1.0e9
    zmax: float = 1.0e9

    def contains(self, x: float, y: float, z: float) -> bool:
        return (
            self.xmin <= x <= self.xmax
            and self.ymin <= y <= self.ymax
            and self.zmin <= z <= self.zmax
        )


@dataclass(frozen=True)
class MissionProfile:
    profile_id: str
    version: int
    allowed_actions: frozenset[str]
    denied_actions: frozenset[str]
    allowed_models: frozenset[str]
    require_signed_models: bool
    geofence: Geofence
    max_agl_m: float | None
    expires_at: datetime | None
    content_hash: str


@dataclass
class MissionPolicyGate:
    profile: MissionProfile
    _decisions: list[PolicyDecisionMsg] = field(default_factory=list)

    def allow_action(
        self,
        action: str,
        *,
        x: float = 0.0,
        y: float = 0.0,
        z: float = 0.0,
        model_id: str = "",
        model_signed: bool = True,
        trace_id: str = "",
        stamp_s: float = 0.0,
    ) -> PolicyDecisionMsg:
        reason = ""
        allowed = True
        act = action.upper()
        if act in self.profile.denied_actions:
            allowed = False
            reason = f"denied_actions:{act}"
        elif act not in self.profile.allowed_actions:
            allowed = False
            reason = f"not_allowed:{act}"
        elif self.profile.expires_at is not None:
            now = datetime.now(timezone.utc)
            if now > self.profile.expires_at:
                allowed = False
                reason = "profile_expired"
        if allowed and not self.profile.geofence.contains(x, y, z):
            allowed = False
            reason = "geofence"
        if allowed and self.profile.max_agl_m is not None and z > self.profile.max_agl_m:
            allowed = False
            reason = "max_agl"
        if allowed and model_id and self.profile.allowed_models:
            if model_id not in self.profile.allowed_models:
                allowed = False
                reason = f"model_not_allowed:{model_id}"
        if allowed and self.profile.require_signed_models and model_id and not model_signed:
            allowed = False
            reason = "unsigned_model"
        dec = PolicyDecisionMsg(
            action=act,
            allowed=allowed,
            reason=reason,
            trace_id=trace_id,
            stamp_s=stamp_s,
        )
        self._decisions.append(dec)
        return dec


def _parse_expires(raw: Any) -> datetime | None:
    if raw in (None, "", "never"):
        return None
    s = str(raw).replace("Z", "+00:00")
    return datetime.fromisoformat(s)


def load_mission_profile(path: Path) -> MissionProfile:
    text = path.read_text(encoding="utf-8")
    raw = yaml.safe_load(text)
    if not isinstance(raw, dict):
        raise ValueError(f"invalid mission profile {path}")
    gf_raw = raw.get("geofence") or {}
    geofence = Geofence(
        xmin=float(gf_raw.get("xmin", -1.0e9)),
        xmax=float(gf_raw.get("xmax", 1.0e9)),
        ymin=float(gf_raw.get("ymin", -1.0e9)),
        ymax=float(gf_raw.get("ymax", 1.0e9)),
        zmin=float(gf_raw.get("zmin", -1.0e9)),
        zmax=float(gf_raw.get("zmax", 1.0e9)),
    )
    allowed = frozenset(str(a).upper() for a in (raw.get("allowed_actions") or []))
    denied = frozenset(str(a).upper() for a in (raw.get("denied_actions") or []))
    models = frozenset(str(m) for m in (raw.get("allowed_models") or []))
    content_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
    max_agl = raw.get("max_agl_m")
    return MissionProfile(
        profile_id=str(raw["profile_id"]),
        version=int(raw.get("version", 1)),
        allowed_actions=allowed,
        denied_actions=denied,
        allowed_models=models,
        require_signed_models=bool(raw.get("require_signed_models", True)),
        geofence=geofence,
        max_agl_m=float(max_agl) if max_agl is not None else None,
        expires_at=_parse_expires(raw.get("expires_at")),
        content_hash=content_hash,
    )
