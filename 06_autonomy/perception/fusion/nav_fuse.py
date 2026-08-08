"""Fuse FC nav + VIO → /bd/nav/fused (covariance-weighted)."""

from __future__ import annotations

from soft_bus.messages import NavStateMsg, VioStateMsg


def fuse_nav_vio(
    fc: NavStateMsg | None,
    vio: VioStateMsg | None,
    *,
    stamp_s: float,
) -> NavStateMsg:
    if fc is None and vio is None:
        return NavStateMsg(stamp_s=stamp_s, source="fused", frame_id="enu")
    if vio is None or vio.status in ("uninit", "diverge"):
        if fc is None:
            return NavStateMsg(stamp_s=stamp_s, source="fused", frame_id="enu")
        return NavStateMsg(
            x=fc.x,
            y=fc.y,
            z=fc.z,
            vx=fc.vx,
            vy=fc.vy,
            vz=fc.vz,
            yaw=fc.yaw,
            stamp_s=stamp_s,
            stamp_ns=fc.stamp_ns,
            sensor_stamp_ns=fc.sensor_stamp_ns,
            frame_id="enu",
            cov_xx=fc.cov_xx,
            cov_yy=fc.cov_yy,
            cov_zz=fc.cov_zz,
            source="fc",
        )
    if fc is None:
        return NavStateMsg(
            x=vio.x,
            y=vio.y,
            z=vio.z,
            vx=vio.vx,
            vy=vio.vy,
            vz=vio.vz,
            yaw=0.0,
            stamp_s=stamp_s,
            stamp_ns=vio.stamp_ns,
            sensor_stamp_ns=vio.sensor_stamp_ns,
            frame_id="enu",
            cov_xx=vio.cov_xx,
            cov_yy=vio.cov_yy,
            cov_zz=vio.cov_zz,
            source="vio",
        )

    # Inverse-variance blend on position; yaw from FC (mag/GPS).
    def blend(a: float, va: float, b: float, vb: float) -> tuple[float, float]:
        wa = 1.0 / max(va, 1e-9)
        wb = 1.0 / max(vb, 1e-9)
        v = 1.0 / (wa + wb)
        return (wa * a + wb * b) * v, v

    x, cx = blend(fc.x, fc.cov_xx, vio.x, vio.cov_xx)
    y, cy = blend(fc.y, fc.cov_yy, vio.y, vio.cov_yy)
    z, cz = blend(fc.z, fc.cov_zz, vio.z, vio.cov_zz)
    return NavStateMsg(
        x=x,
        y=y,
        z=z,
        vx=0.5 * (fc.vx + vio.vx),
        vy=0.5 * (fc.vy + vio.vy),
        vz=0.5 * (fc.vz + vio.vz),
        yaw=fc.yaw,
        stamp_s=stamp_s,
        stamp_ns=max(fc.stamp_ns, vio.stamp_ns),
        sensor_stamp_ns=max(fc.sensor_stamp_ns, vio.sensor_stamp_ns),
        frame_id="enu",
        cov_xx=cx,
        cov_yy=cy,
        cov_zz=cz,
        source="fused",
    )
