"""GSC envelope authority + territorial COP ingest. No cameras. No L0."""

from __future__ import annotations

import time

from dmi.envelope import EnvelopeController
from dmi.messages import TOPIC_DMI_AGENT_STATUS, AgentStatus
from dmi.territorial import CopOrigin, TerritorialCop, cop_radius_for_envelope
from soft_bus.bus import SoftBus
from soft_bus.messages import (
    TOPIC_ENVELOPE_SWITCH,
    TOPIC_MISSION_ENVELOPE,
    TOPIC_MISSION_PROFILE,
    TOPIC_POLICY_DECISION,
    TOPIC_TERRITORIAL_INGEST,
    TOPIC_TERRITORIAL_TRACK,
    EnvelopeMsg,
    EnvelopeSwitchMsg,
    MissionProfileMsg,
    PolicyDecisionMsg,
    TerritorialIngestMsg,
    TerritorialTrackMsg,
)


class EnvelopeSoftNode:
    def __init__(
        self,
        bus: SoftBus,
        *,
        origin: CopOrigin | None = None,
        stamp_s: float = 0.0,
    ) -> None:
        self.bus = bus
        self.ctrl = EnvelopeController(stamp_s=stamp_s)
        self.origin = origin or CopOrigin(lat=55.75, lon=37.62)
        self.cop = TerritorialCop(
            self.origin,
            cop_radius_for_envelope(self.ctrl.profile.envelope, self.ctrl.profile.cop_radius_m),
        )
        bus.subscribe(TOPIC_ENVELOPE_SWITCH, self._on_switch)
        bus.subscribe(TOPIC_TERRITORIAL_INGEST, self._on_ingest)
        bus.subscribe(TOPIC_DMI_AGENT_STATUS, self._on_agent)
        self._publish_envelope(self.ctrl.state, committed=True)

    def _rebuild_cop(self) -> None:
        friends = set(self.cop.friend_ids)
        self.cop = TerritorialCop(
            self.origin,
            cop_radius_for_envelope(self.ctrl.profile.envelope, self.ctrl.profile.cop_radius_m),
        )
        self.cop.set_friends(friends)

    def _on_agent(self, st: AgentStatus) -> None:
        self.cop.friend_ids.add(st.agent_id)
        self.cop.recorrelate()

    def _on_switch(self, msg: EnvelopeSwitchMsg) -> None:
        now = msg.stamp_s or time.time()
        state, committed = self.ctrl.switch(
            msg.envelope,
            msg.profile_id,
            operator_ack=bool(msg.operator_ack),
            stamp_s=now,
        )
        self.bus.publish(
            TOPIC_POLICY_DECISION,
            PolicyDecisionMsg(
                action="ENVELOPE_SWITCH",
                allowed=committed,
                reason=state.reason,
                stamp_s=now,
            ),
        )
        if committed:
            self._rebuild_cop()
        self._publish_envelope(state, committed=committed)

    def _on_ingest(self, msg: TerritorialIngestMsg) -> None:
        if "INGEST_TERRITORIAL" not in self.ctrl.profile.allowed_actions:
            self.bus.publish(
                TOPIC_POLICY_DECISION,
                PolicyDecisionMsg(
                    action="INGEST_TERRITORIAL",
                    allowed=False,
                    reason="not_allowed:INGEST_TERRITORIAL",
                    stamp_s=msg.stamp_s,
                ),
            )
            return
        tr = self.cop.ingest(
            track_id=msg.track_id,
            source=msg.source,
            lat=msg.lat,
            lon=msg.lon,
            alt_m=msg.alt_m,
            ident=msg.ident,
            stamp_s=msg.stamp_s,
        )
        if tr is None:
            return
        self.bus.publish(
            TOPIC_TERRITORIAL_TRACK,
            TerritorialTrackMsg(
                track_id=tr.track_id,
                source=tr.source,
                lat=tr.lat,
                lon=tr.lon,
                alt_m=tr.alt_m,
                ident=tr.ident,
                affiliation=tr.affiliation,
                range_m=tr.range_m,
                stamp_s=tr.stamp_s,
            ),
        )

    def _publish_envelope(self, state, *, committed: bool) -> None:
        if not committed:
            live = self.ctrl.state
            self.bus.publish(
                TOPIC_MISSION_ENVELOPE,
                EnvelopeMsg(
                    envelope=live.kind.value,
                    profile_id=live.profile_id,
                    content_hash=live.content_hash,
                    stamp_s=state.stamp_s,
                    reason=state.reason,
                    operator_ack=live.operator_ack,
                ),
            )
            return
        p = self.ctrl.profile
        self.bus.publish(
            TOPIC_MISSION_ENVELOPE,
            EnvelopeMsg(
                envelope=state.kind.value,
                profile_id=state.profile_id,
                content_hash=state.content_hash,
                stamp_s=state.stamp_s,
                reason=state.reason,
                operator_ack=state.operator_ack,
            ),
        )
        self.bus.publish(
            TOPIC_MISSION_PROFILE,
            MissionProfileMsg(
                profile_id=p.profile_id,
                version=p.version,
                content_hash=p.content_hash,
                stamp_s=state.stamp_s,
                envelope=p.envelope.value,
            ),
        )


def main(bus: SoftBus | None = None) -> SoftBus:
    bus = bus or SoftBus()
    EnvelopeSoftNode(bus)
    return bus


if __name__ == "__main__":
    main()
    print("envelope soft node ready")
