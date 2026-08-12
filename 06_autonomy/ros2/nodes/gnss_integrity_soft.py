"""Onboard GNSS integrity publisher. Own-ship jam/spoof detect only."""

from __future__ import annotations

from dmi.gnss_integrity import GnssIntegrityMonitor
from soft_bus.bus import SoftBus
from soft_bus.messages import (
    TOPIC_GNSS,
    TOPIC_GNSS_INTEGRITY,
    GnssFix,
    GnssIntegrityMsg,
)


class GnssIntegritySoftNode:
    def __init__(self, bus: SoftBus) -> None:
        self.bus = bus
        self.mon = GnssIntegrityMonitor()
        bus.subscribe(TOPIC_GNSS, self._on_gnss)

    def _on_gnss(self, fix: GnssFix) -> None:
        st = self.mon.update(fix)
        self.bus.publish(
            TOPIC_GNSS_INTEGRITY,
            GnssIntegrityMsg(
                ok=st.ok,
                reason=st.reason,
                hdop=st.hdop,
                jump_m=st.jump_m,
                stamp_s=st.stamp_s,
            ),
        )


def main(bus: SoftBus | None = None) -> SoftBus:
    bus = bus or SoftBus()
    GnssIntegritySoftNode(bus)
    return bus


if __name__ == "__main__":
    main()
    print("gnss integrity soft node ready")
