"""Publish active calibration hashes on SoftBus."""

from __future__ import annotations

import time
from pathlib import Path

from perception.calibration.loader import CalibBundle, load_calib_bundle
from soft_bus.bus import SoftBus
from soft_bus.messages import TOPIC_CALIB_ACTIVE, CalibActiveMsg


def _default_calib_dir() -> Path:
    return Path(__file__).resolve().parents[2] / "calib"


class CalibSoftNode:
    def __init__(
        self,
        bus: SoftBus,
        *,
        calib_dir: Path | None = None,
    ) -> None:
        self.bus = bus
        root = calib_dir or _default_calib_dir()
        self.bundle = load_calib_bundle(
            root / "camera_forward.yaml",
            root / "extrinsics.yaml",
            root / "imu0.yaml",
        )
        self.publish()

    def publish(self) -> CalibActiveMsg:
        msg = CalibActiveMsg(
            camera_hash=self.bundle.camera_hash,
            imu_hash=self.bundle.imu_hash,
            extrinsics_hash=self.bundle.extrinsics_hash,
            stamp_s=time.time(),
            ok=self.bundle.ok,
        )
        self.bus.publish(TOPIC_CALIB_ACTIVE, msg)
        return msg


def load_default_bundle() -> CalibBundle:
    root = _default_calib_dir()
    return load_calib_bundle(
        root / "camera_forward.yaml",
        root / "extrinsics.yaml",
        root / "imu0.yaml",
    )


def main(bus: SoftBus | None = None) -> SoftBus:
    bus = bus or SoftBus()
    CalibSoftNode(bus)
    return bus


if __name__ == "__main__":
    main()
