"""GSC territorial COP 30–50 km. GNSS / Remote ID / ERA-GLONASS ingest — not CERBER EO."""

from __future__ import annotations

import math
from dataclasses import dataclass

from .mission_policy import EnvelopeKind

EARTH_R_M = 6371000.0
AFFILIATION_FRIEND = "friend"
AFFILIATION_UNKNOWN = "unknown"
SOURCES = frozenset({"remote_id", "era_glonass", "adsb", "operator", "own_swarm"})


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2.0) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2.0) ** 2
    return 2.0 * EARTH_R_M * math.asin(min(1.0, math.sqrt(a)))


def affiliation_of(ident: str, friend_ids: set[str]) -> str:
    if ident and ident in friend_ids:
        return AFFILIATION_FRIEND
    return AFFILIATION_UNKNOWN


@dataclass
class TerritorialTrack:
    track_id: str
    source: str
    lat: float
    lon: float
    alt_m: float
    ident: str
    affiliation: str
    range_m: float
    stamp_s: float = 0.0

    def __post_init__(self) -> None:
        if self.source not in SOURCES:
            raise ValueError(f"unknown territorial source {self.source!r}")
        if self.affiliation not in (AFFILIATION_FRIEND, AFFILIATION_UNKNOWN):
            raise ValueError("affiliation is friend|unknown — FOE is not a detector class")


@dataclass
class CopOrigin:
    lat: float
    lon: float
    alt_m: float = 0.0


class TerritorialCop:
    """GSC picture. Airframe geofence stays on MissionProfile.geofence."""

    def __init__(self, origin: CopOrigin, radius_m: float) -> None:
        if radius_m <= 0.0:
            raise ValueError("cop radius must be > 0")
        self.origin = origin
        self.radius_m = float(radius_m)
        self._tracks: dict[str, TerritorialTrack] = {}
        self.friend_ids: set[str] = set()

    def set_friends(self, ids: set[str]) -> None:
        self.friend_ids = set(ids)

    def ingest(
        self,
        *,
        track_id: str,
        source: str,
        lat: float,
        lon: float,
        alt_m: float,
        ident: str,
        stamp_s: float,
    ) -> TerritorialTrack | None:
        rng = haversine_m(self.origin.lat, self.origin.lon, lat, lon)
        if rng > self.radius_m:
            return None
        tr = TerritorialTrack(
            track_id=track_id,
            source=source,
            lat=lat,
            lon=lon,
            alt_m=alt_m,
            ident=ident,
            affiliation=affiliation_of(ident, self.friend_ids),
            range_m=rng,
            stamp_s=stamp_s,
        )
        self._tracks[track_id] = tr
        return tr

    def get(self, track_id: str) -> TerritorialTrack | None:
        return self._tracks.get(track_id)

    def tracks(self) -> list[TerritorialTrack]:
        return list(self._tracks.values())

    def recorrelate(self) -> None:
        for tid, tr in list(self._tracks.items()):
            self._tracks[tid] = TerritorialTrack(
                track_id=tr.track_id,
                source=tr.source,
                lat=tr.lat,
                lon=tr.lon,
                alt_m=tr.alt_m,
                ident=tr.ident,
                affiliation=affiliation_of(tr.ident, self.friend_ids),
                range_m=tr.range_m,
                stamp_s=tr.stamp_s,
            )


def cop_radius_for_envelope(envelope: EnvelopeKind, profile_radius_m: float) -> float:
    if envelope is EnvelopeKind.CIVIL:
        return min(profile_radius_m, 10_000.0)
    return profile_radius_m
