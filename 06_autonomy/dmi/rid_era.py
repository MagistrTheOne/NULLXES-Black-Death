"""RF 2026 Remote ID / ЭРА-ГЛОНАСС hooks. Interface payloads — not a certified GOST stack."""

from __future__ import annotations

from dataclasses import dataclass

from .mission_policy import EnvelopeKind, MissionProfile

# ПП РФ №1701: БВС ≥0.25 кг — удалённая идентификация (индекс, категория, высота, координаты).
# ПП от 02.02.2026 №83 / ЭРА-ГЛОНАСС: гражданский контур учёта с 01.03.2026.
RID_MAX_AGE_S = 2.0
EMERGENCY_MODES = frozenset({"RTL", "LAND", "SAFE_LAND"})


@dataclass(frozen=True)
class RidBroadcast:
    ident: str
    category: str
    lat: float
    lon: float
    alt_m: float
    stamp_s: float
    dest: str = "era_glonass"


@dataclass(frozen=True)
class EmergencyTermination:
    mode: str
    stamp_s: float

    def __post_init__(self) -> None:
        if self.mode not in EMERGENCY_MODES:
            raise ValueError(f"emergency mode must be one of {sorted(EMERGENCY_MODES)}")


def rid_required(profile: MissionProfile) -> bool:
    return profile.envelope is EnvelopeKind.CIVIL and profile.rid_required


def rid_should_broadcast(profile: MissionProfile) -> bool:
    if profile.envelope is EnvelopeKind.CIVIL:
        return True
    return profile.rid_broadcast


def rid_gate(profile: MissionProfile, last_rid_age_s: float | None, *, stamp_s: float) -> tuple[bool, str]:
    """CIVIL: stale/missing RID blocks TAKEOFF-class actions. DEFENSE: hold is policy, not a jammer."""
    if not rid_required(profile):
        return True, ""
    if last_rid_age_s is None:
        return False, "rid_missing"
    if last_rid_age_s > RID_MAX_AGE_S:
        return False, "rid_stale"
    return True, ""


def make_rid(
    *,
    ident: str,
    category: str,
    lat: float,
    lon: float,
    alt_m: float,
    stamp_s: float,
) -> RidBroadcast:
    if not ident:
        raise ValueError("RID ident empty")
    return RidBroadcast(
        ident=ident,
        category=category,
        lat=lat,
        lon=lon,
        alt_m=alt_m,
        stamp_s=stamp_s,
        dest="era_glonass",
    )
