"""Onboard Remote ID / ЭРА-ГЛОНАСС shaped broadcast. CIVIL required. DEFENSE hold allowed."""

from __future__ import annotations

import time

from dmi.mission_policy import EnvelopeKind, MissionProfile, load_mission_profile
from dmi.envelope import DEFAULT_CIVIL_PROFILE_ID, profile_path_for
from dmi.rid_era import make_rid, rid_should_broadcast
from soft_bus.bus import SoftBus
from soft_bus.messages import (
    TOPIC_GNSS,
    TOPIC_MISSION_ENVELOPE,
    TOPIC_RID_BROADCAST,
    EnvelopeMsg,
    GnssFix,
    RidBroadcastMsg,
)


class RidSoftNode:
    def __init__(
        self,
        bus: SoftBus,
        *,
        ident: str,
        category: str = "bas_civil",
        min_period_s: float = 1.0,
    ) -> None:
        self.bus = bus
        self.ident = ident
        self.category = category
        self.min_period_s = min_period_s
        path = profile_path_for(DEFAULT_CIVIL_PROFILE_ID, EnvelopeKind.CIVIL)
        self.profile: MissionProfile = load_mission_profile(path)
        self._last_pub = -1e9
        self._fix: GnssFix | None = None
        bus.subscribe(TOPIC_MISSION_ENVELOPE, self._on_envelope)
        bus.subscribe(TOPIC_GNSS, self._on_gnss)

    def _on_envelope(self, msg: EnvelopeMsg) -> None:
        kind = EnvelopeKind.DEFENSE if msg.envelope == "defense" else EnvelopeKind.CIVIL
        path = profile_path_for(msg.profile_id, kind)
        if path.is_file():
            self.profile = load_mission_profile(path)

    def _on_gnss(self, fix: GnssFix) -> None:
        self._fix = fix
        self.pulse(now_s=fix.stamp_s or time.time())

    def pulse(self, *, now_s: float | None = None) -> None:
        if not rid_should_broadcast(self.profile):
            return
        fix = self._fix
        if fix is None or not fix.fix_ok:
            return
        t = now_s if now_s is not None else time.time()
        if t - self._last_pub < self.min_period_s:
            return
        rid = make_rid(
            ident=self.ident,
            category=self.category,
            lat=fix.lat_deg,
            lon=fix.lon_deg,
            alt_m=fix.alt_amsl_m if fix.alt_amsl_m else fix.z,
            stamp_s=t,
        )
        self._last_pub = t
        self.bus.publish(
            TOPIC_RID_BROADCAST,
            RidBroadcastMsg(
                ident=rid.ident,
                category=rid.category,
                lat=rid.lat,
                lon=rid.lon,
                alt_m=rid.alt_m,
                stamp_s=rid.stamp_s,
                dest=rid.dest,
            ),
        )


def main(bus: SoftBus | None = None, ident: str = "RF-BD-ALPHA-001") -> SoftBus:
    bus = bus or SoftBus()
    RidSoftNode(bus, ident=ident)
    return bus


if __name__ == "__main__":
    main()
    print("rid soft node ready")
