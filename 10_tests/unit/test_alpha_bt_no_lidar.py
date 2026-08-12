"""AlphaBT: lidar optional until reported; NOMINAL with cams>=1."""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "06_autonomy"))

from fault_management.detection import DetectedFaults
from fault_management.isolation import IsolationMask
from fault_management.reconfiguration import reconfigure
from planning.behaviour.alpha_bt import AlphaBT, FlightMode, HealthFlags
from soft_bus.messages import TOPIC_NAV_EKF


def _ok(**kw) -> HealthFlags:
    base = dict(
        thrusters_ok=2,
        cams_ok=1,
        imu_ok=1,
        gnss_ok=True,
        lidar_ok=False,
        lidar_reported=False,
        compute_peer_alive=True,
        battery_soc=0.8,
        nav_integrity=True,
    )
    base.update(kw)
    return HealthFlags(**base)


def test_nominal_without_lidar():
    bt = AlphaBT()
    assert bt.tick(_ok()) == FlightMode.NOMINAL


def test_lidar_fail_only_when_reported():
    bt = AlphaBT()
    assert bt.tick(_ok(lidar_reported=True, lidar_ok=False)) == FlightMode.DEGRADED_SENS
    bt2 = AlphaBT()
    assert bt2.tick(_ok(lidar_reported=False, lidar_ok=False)) == FlightMode.NOMINAL


def test_cams_ok_less_than_one_degraded():
    bt = AlphaBT()
    assert bt.tick(_ok(cams_ok=0)) == FlightMode.DEGRADED_SENS


def test_reconfigure_no_lidar_one_cam_nominal():
    faults = DetectedFaults(
        thruster_fail=[],
        cam_fail=[1, 2, 3],
        imu_fail=[],
        gnss_stale=False,
        lidar_fail=False,
        peer_dead=False,
        battery_low=False,
        battery_critical=False,
    )
    mask = IsolationMask(
        motors_enabled=[True, True],
        cams_enabled=[True, False, False, False],
        imus_enabled=[True, True],
        lidar_enabled=True,
        use_gnss=True,
    )
    health, out = reconfigure(faults, mask, lidar_reported=False)
    health.battery_soc = 0.8
    health.compute_peer_alive = True
    assert health.cams_ok == 1
    assert health.lidar_reported is False
    assert out.mode_hint == FlightMode.NOMINAL
    assert AlphaBT().tick(health) == FlightMode.NOMINAL


def test_nav_ekf_topic():
    assert TOPIC_NAV_EKF == "/bd/nav/ekf"
