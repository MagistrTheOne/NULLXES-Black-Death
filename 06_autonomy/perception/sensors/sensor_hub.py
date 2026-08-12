"""SensorHub — publish CAM / IMU / GNSS / time sync / health on SoftBus."""

from __future__ import annotations

import time
from typing import Callable

from soft_bus.bus import SoftBus
from soft_bus.messages import (
    TOPIC_CAM_FORWARD,
    TOPIC_GNSS,
    TOPIC_IMU,
    TOPIC_NAV,
    TOPIC_SENSORHUB_HEALTH,
    TOPIC_TIME_SYNC,
    ImageMsg,
    SensorHubHealth,
    TimeSyncMsg,
)

from perception.trace.recorder import FlightRecorder, new_trace_id

from .camera_source import FrameSource
from .fc_telemetry import FcTelemetry, map_fc_to_bus

_CAM_TOPICS = {
    "forward": TOPIC_CAM_FORWARD,
}


class SensorHub:
    def __init__(
        self,
        bus: SoftBus,
        *,
        camera: FrameSource | None = None,
        fc_poll: Callable[[], FcTelemetry | None] | None = None,
        publish_fc_nav: bool = True,
        recorder: FlightRecorder | None = None,
        agent_id: str = "bd",
    ) -> None:
        self.bus = bus
        self.camera = camera
        self.fc_poll = fc_poll
        self.publish_fc_nav = publish_fc_nav
        self.recorder = recorder or FlightRecorder(bus, agent_id=agent_id)
        self.agent_id = agent_id
        self.dropped_frames = 0
        self._cam_ok = False
        self._imu_ok = False
        self._gnss_ok = False
        self._fc_offset_ns = 0
        self._last_fc_boot_ns = 0
        self.last_trace_id = ""

    def start_camera(self) -> bool:
        if self.camera is None:
            return False
        self._cam_ok = self.camera.open()
        return self._cam_ok

    def stop(self) -> None:
        if self.camera is not None:
            self.camera.close()
        self._cam_ok = False

    def ingest_fc(self, fc: FcTelemetry) -> None:
        """Direct ingest (bench / unit / HIL without live pymavlink)."""
        now_ns = time.monotonic_ns()
        if fc.sensor_stamp_ns:
            self._fc_offset_ns = now_ns - fc.sensor_stamp_ns
            self._last_fc_boot_ns = fc.sensor_stamp_ns
        imu, gnss, nav = map_fc_to_bus(fc, stamp_ns=now_ns)
        self.bus.publish(TOPIC_IMU, imu)
        self.bus.publish(TOPIC_GNSS, gnss)
        if self.publish_fc_nav:
            self.bus.publish(TOPIC_NAV, nav)
        self._imu_ok = bool(fc.imu_sample_ok)
        self._gnss_ok = gnss.fix_ok
        self.bus.publish(
            TOPIC_TIME_SYNC,
            TimeSyncMsg(
                cam_imu_offset_ns=0,
                fc_offset_ns=self._fc_offset_ns,
                stamp_ns=now_ns,
                quality="coarse",
            ),
        )
        self._publish_health(now_ns / 1e9)

    def pulse(self) -> None:
        """One hub cycle: camera frame + optional FC poll."""
        now_ns = time.monotonic_ns()
        now_s = now_ns / 1e9

        if self.camera is not None and self._cam_ok:
            frame = self.camera.read()
            if frame is None:
                self.dropped_frames += 1
                self._cam_ok = False
            else:
                self._cam_ok = True
                topic = _CAM_TOPICS.get(self.camera.name, TOPIC_CAM_FORWARD)
                trace_id = new_trace_id(self.agent_id)
                self.last_trace_id = trace_id
                with self.recorder.span("sensorhub", trace_id=trace_id, attrs={"seq": str(frame.seq)}):
                    self.bus.publish(
                        topic,
                        ImageMsg(
                            bgr=frame.bgr,
                            camera=self.camera.name,
                            stamp_s=now_s,
                            stamp_ns=now_ns,
                            sensor_stamp_ns=frame.sensor_stamp_ns,
                            frame_id=f"cam_{self.camera.name}",
                            seq=frame.seq,
                            trace_id=trace_id,
                        ),
                    )

        if self.fc_poll is not None:
            sample = self.fc_poll()
            if sample is not None:
                self.ingest_fc(sample)

        self._publish_health(now_s)

    def _publish_health(self, stamp_s: float) -> None:
        self.bus.publish(
            TOPIC_SENSORHUB_HEALTH,
            SensorHubHealth(
                cam_ok=self._cam_ok,
                imu_ok=self._imu_ok,
                gnss_ok=self._gnss_ok,
                dropped_frames=self.dropped_frames,
                detail="",
                stamp_s=stamp_s,
            ),
        )
