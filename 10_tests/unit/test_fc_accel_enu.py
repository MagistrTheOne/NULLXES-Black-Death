"""FC body specific force → ENU linear accel; imu_ok only after SCALED_IMU."""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "06_autonomy"))

from perception.sensors.fc_telemetry import G_MPS2, FcTelemetry, body_accel_to_enu_linear, map_fc_to_bus
from perception.sensors.sensor_hub import SensorHub
from soft_bus.bus import SoftBus
from soft_bus.messages import TOPIC_SENSORHUB_HEALTH, SensorHubHealth


def test_hover_body_zg_is_zero_linear_enu():
    ax, ay, az = body_accel_to_enu_linear(0.0, 0.0, 0.0, 0.0, 0.0, G_MPS2)
    assert abs(ax) < 1e-6
    assert abs(ay) < 1e-6
    assert abs(az) < 1e-6


def test_gps_stamp_from_time_boot_ms():
    fc = FcTelemetry(time_boot_ms=1500, imu_sample_ok=True, accel_z=G_MPS2, fix_ok=True)
    imu, gnss, nav = map_fc_to_bus(fc, stamp_ns=9_000_000_000)
    assert gnss.sensor_stamp_ns == 1_500_000_000
    assert imu.sensor_stamp_ns == 1_500_000_000
    assert nav.sensor_stamp_ns == 1_500_000_000
    assert imu.frame_id == "enu"
    assert abs(imu.accel_mps2[0]) < 1e-5
    assert abs(imu.accel_mps2[1]) < 1e-5
    assert abs(imu.accel_mps2[2]) < 1e-5


def test_no_imu_sample_zeros_accel():
    imu, _gnss, _nav = map_fc_to_bus(FcTelemetry(accel_z=G_MPS2, imu_sample_ok=False))
    assert imu.accel_mps2 == (0.0, 0.0, 0.0)


def test_sensorhub_imu_ok_only_after_sample():
    bus = SoftBus()
    health: list[SensorHubHealth] = []
    bus.subscribe(TOPIC_SENSORHUB_HEALTH, health.append)
    hub = SensorHub(bus)
    hub.ingest_fc(FcTelemetry(fix_ok=True, north_m=1.0))
    assert health[-1].imu_ok is False
    hub.ingest_fc(FcTelemetry(fix_ok=True, imu_sample_ok=True, accel_z=G_MPS2))
    assert health[-1].imu_ok is True
