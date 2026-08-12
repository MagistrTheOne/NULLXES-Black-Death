"""VIO SoftBus node — IVioProvider → /bd/nav/vio (+ optional fuse)."""

from __future__ import annotations

import time

from perception.fusion.nav_fuse import fuse_nav_vio
from perception.slam.ivio import (
    BasaltProvider,
    IVioProvider,
    NullVioProvider,
    NullxesVoProvider,
    OpenVinsProvider,
)
from soft_bus.bus import SoftBus
from soft_bus.messages import (
    TOPIC_CAM_FORWARD,
    TOPIC_IMU,
    TOPIC_NAV,
    TOPIC_NAV_FUSED,
    TOPIC_NAV_VIO,
    ImageMsg,
    ImuMsg,
    NavStateMsg,
)


def make_provider(name: str) -> IVioProvider:
    key = name.lower()
    if key in ("nullxes_vo", "nullxesvo", "nullxes"):
        return NullxesVoProvider()
    if key in ("openvins", "openvinsprovider"):
        return OpenVinsProvider()
    if key in ("basalt", "basaltprovider"):
        return BasaltProvider()
    return NullVioProvider()


class VioSoftNode:
    def __init__(
        self,
        bus: SoftBus,
        *,
        provider: str = "nullxes_vo",
        publish_fused: bool = True,
    ) -> None:
        self.bus = bus
        self.provider = make_provider(provider)
        self.publish_fused = publish_fused
        self._fc_nav: NavStateMsg | None = None
        bus.subscribe(TOPIC_IMU, self._on_imu)
        bus.subscribe(TOPIC_CAM_FORWARD, self._on_image)
        bus.subscribe(TOPIC_NAV, self._on_nav)

    def _on_nav(self, nav: NavStateMsg) -> None:
        if nav.source in ("fc", ""):
            self._fc_nav = nav

    def _on_imu(self, imu: ImuMsg) -> None:
        self.provider.push_imu(imu)

    def _on_image(self, image: ImageMsg) -> None:
        vio = self.provider.push_image(image)
        if vio is None:
            return
        self.bus.publish(TOPIC_NAV_VIO, vio)
        if self.publish_fused:
            fused = fuse_nav_vio(self._fc_nav, vio, stamp_s=image.stamp_s or time.time())
            self.bus.publish(TOPIC_NAV_FUSED, fused)


def main(bus: SoftBus | None = None, provider: str = "nullxes_vo") -> SoftBus:
    bus = bus or SoftBus()
    VioSoftNode(bus, provider=provider)
    return bus


if __name__ == "__main__":
    main()
