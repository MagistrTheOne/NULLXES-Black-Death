"""SensorHub SoftBus node."""

from __future__ import annotations

from perception.sensors.camera_source import FrameSource, OpenCvCameraSource
from perception.sensors.fc_telemetry import FcTelemetry
from perception.sensors.sensor_hub import SensorHub
from soft_bus.bus import SoftBus


class SensorHubSoftNode:
    def __init__(
        self,
        bus: SoftBus,
        *,
        camera: FrameSource | None = None,
        camera_device: int | str | None = None,
        publish_fc_nav: bool = True,
    ) -> None:
        cam = camera
        if cam is None and camera_device is not None:
            cam = OpenCvCameraSource(camera_device, camera_name="forward")
        self.hub = SensorHub(bus, camera=cam, publish_fc_nav=publish_fc_nav)
        if cam is not None:
            self.hub.start_camera()

    def ingest_fc(self, fc: FcTelemetry) -> None:
        self.hub.ingest_fc(fc)

    def pulse(self) -> None:
        self.hub.pulse()

    def stop(self) -> None:
        self.hub.stop()


def main(bus: SoftBus | None = None, camera_device: int | str | None = None) -> SoftBus:
    bus = bus or SoftBus()
    SensorHubSoftNode(bus, camera_device=camera_device)
    return bus


if __name__ == "__main__":
    main()
