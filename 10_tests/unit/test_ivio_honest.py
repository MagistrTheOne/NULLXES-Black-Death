"""VIO providers: OpenVINS/Basalt uninit; nullxes_vo IMU gate; fuse FC-only on degraded."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "06_autonomy"))

from perception.fusion.nav_fuse import fuse_nav_vio
from perception.slam.ivio import BasaltProvider, NullxesVoProvider, OpenVinsProvider
from soft_bus.messages import ImageMsg, ImuMsg, NavStateMsg


def _img(stamp_ns: int = 1) -> ImageMsg:
    return ImageMsg(bgr=np.zeros((48, 64, 3), dtype=np.uint8), stamp_s=1.0, stamp_ns=stamp_ns)


def test_openvins_basalt_uninit():
    img = _img()
    ov = OpenVinsProvider().push_image(img)
    ba = BasaltProvider().push_image(img)
    assert ov is not None and ba is not None
    assert ov.provider == "openvins" and ov.status == "uninit"
    assert ba.provider == "basalt" and ba.status == "uninit"


def test_nullxes_vo_imu_zero_skips_integrate():
    vo = NullxesVoProvider()
    vo.push_imu(ImuMsg(accel_mps2=(0.0, 0.0, 0.0), stamp_ns=1_000_000, sensor_stamp_ns=1_000_000))
    vo.push_imu(ImuMsg(accel_mps2=(0.05, 0.0, 0.0), stamp_ns=2_000_000_000, sensor_stamp_ns=2_000_000_000))
    assert vo._pose.x == 0.0 and vo._pose.vx == 0.0


def test_nullxes_vo_imu_accel_integrates():
    vo = NullxesVoProvider()
    vo.push_imu(ImuMsg(accel_mps2=(2.0, 0.0, 0.0), stamp_ns=1_000_000, sensor_stamp_ns=1_000_000))
    vo.push_imu(ImuMsg(accel_mps2=(2.0, 0.0, 0.0), stamp_ns=1_000_000_000, sensor_stamp_ns=1_000_000_000))
    assert vo._pose.x != 0.0


def test_nullxes_vo_first_frame_uninit():
    vo = NullxesVoProvider()
    msg = vo.push_image(_img())
    assert msg is not None
    assert msg.status == "uninit"
    assert msg.provider == "nullxes_vo"


def test_fuse_degraded_and_uninit_fc_only():
    fc = NavStateMsg(x=10.0, y=20.0, z=30.0, yaw=0.5, cov_xx=4, cov_yy=4, cov_zz=4, source="fc")
    from soft_bus.messages import VioStateMsg

    degraded = VioStateMsg(x=99, y=99, z=99, status="degraded", provider="nullxes_vo", cov_xx=1, cov_yy=1, cov_zz=1)
    uninit = VioStateMsg(status="uninit", provider="openvins")
    f1 = fuse_nav_vio(fc, degraded, stamp_s=1.0)
    f2 = fuse_nav_vio(fc, uninit, stamp_s=1.0)
    assert f1.source == "fc" and f1.x == 10.0
    assert f2.source == "fc" and f2.y == 20.0
