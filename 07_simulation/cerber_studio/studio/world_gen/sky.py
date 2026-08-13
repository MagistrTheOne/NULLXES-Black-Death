"""Sky dome, sun, haze. TOD / weather palettes."""

from __future__ import annotations

import math

from panda3d.core import (
    AmbientLight,
    DirectionalLight,
    Fog,
    Geom,
    GeomNode,
    GeomTriangles,
    GeomVertexData,
    GeomVertexFormat,
    GeomVertexWriter,
    NodePath,
    Vec3,
    Vec4,
)

from .weather import AtmosphereState

SKY_RADIUS = 72000.0

PALETTES = {
    "clear": {
        "zenith": (0.28, 0.48, 0.78),
        "horizon": (0.78, 0.84, 0.90),
        "haze": (0.70, 0.76, 0.82),
        "ambient": (0.42, 0.45, 0.50, 1),
        "sun": (1.0, 0.96, 0.88, 1),
        "bg": (0.70, 0.76, 0.82, 1),
    },
    "sunset": {
        "zenith": (0.18, 0.22, 0.42),
        "horizon": (0.92, 0.52, 0.28),
        "haze": (0.72, 0.48, 0.36),
        "ambient": (0.38, 0.28, 0.26, 1),
        "sun": (1.0, 0.62, 0.32, 1),
        "bg": (0.72, 0.48, 0.36, 1),
    },
    "overcast": {
        "zenith": (0.42, 0.46, 0.50),
        "horizon": (0.62, 0.64, 0.66),
        "haze": (0.58, 0.60, 0.62),
        "ambient": (0.48, 0.50, 0.52, 1),
        "sun": (0.72, 0.74, 0.76, 1),
        "bg": (0.58, 0.60, 0.62, 1),
    },
    "night": {
        "zenith": (0.04, 0.05, 0.10),
        "horizon": (0.10, 0.12, 0.18),
        "haze": (0.08, 0.09, 0.12),
        "ambient": (0.16, 0.18, 0.22, 1),
        "sun": (0.35, 0.40, 0.55, 1),
        "bg": (0.08, 0.09, 0.12, 1),
    },
    "rain": {
        "zenith": (0.30, 0.34, 0.38),
        "horizon": (0.48, 0.50, 0.52),
        "haze": (0.44, 0.46, 0.48),
        "ambient": (0.36, 0.38, 0.40, 1),
        "sun": (0.55, 0.56, 0.58, 1),
        "bg": (0.44, 0.46, 0.48, 1),
    },
    "fog": {
        "zenith": (0.55, 0.58, 0.60),
        "horizon": (0.70, 0.72, 0.74),
        "haze": (0.68, 0.70, 0.72),
        "ambient": (0.50, 0.52, 0.54, 1),
        "sun": (0.80, 0.82, 0.84, 1),
        "bg": (0.68, 0.70, 0.72, 1),
    },
    "storm": {
        "zenith": (0.16, 0.18, 0.22),
        "horizon": (0.28, 0.30, 0.32),
        "haze": (0.22, 0.24, 0.26),
        "ambient": (0.22, 0.24, 0.28, 1),
        "sun": (0.40, 0.42, 0.48, 1),
        "bg": (0.22, 0.24, 0.26, 1),
    },
}


def _lerp(a, b, t: float):
    return tuple(a[i] + (b[i] - a[i]) * t for i in range(len(a)))


def palette_for(atmos: AtmosphereState) -> dict:
    night = PALETTES["night"]
    day = PALETTES["clear"]
    dusk = PALETTES["sunset"]
    over = PALETTES["overcast"]
    el = atmos.sun_elevation
    cloud = max(0.0, min(1.0, atmos.cloudiness))
    if el >= 12.0:
        pal = {k: _lerp(day[k], over[k], cloud) for k in day}
    elif el >= 0.0:
        t = 1.0 - el / 12.0
        mix = {k: _lerp(day[k], dusk[k], t) for k in day}
        pal = {k: _lerp(mix[k], over[k], cloud * 0.65) for k in day}
    elif el >= -6.0:
        t = (el + 6.0) / 6.0
        pal = {k: _lerp(night[k], dusk[k], t) for k in day}
    else:
        pal = dict(night)
    vis = max(1.0, atmos.visibility_km)
    fog_boost = max(0.0, min(1.0, 1.0 - vis / 40.0))
    pal["haze"] = _lerp(pal["haze"], over["haze"], fog_boost)
    return pal


def _sky_dome_build(rings: int, segs: int, radius: float, zenith, horizon) -> GeomNode:
    fmt = GeomVertexFormat.getV3c4()
    vdata = GeomVertexData("sky", fmt, Geom.UHStatic)
    vertex = GeomVertexWriter(vdata, "vertex")
    color = GeomVertexWriter(vdata, "color")
    idx = []
    for r in range(rings + 1):
        t = r / rings
        fade = t ** 1.35
        cr = horizon[0] * (1.0 - fade) + zenith[0] * fade
        cg = horizon[1] * (1.0 - fade) + zenith[1] * fade
        cb = horizon[2] * (1.0 - fade) + zenith[2] * fade
        elev = t * math.pi * 0.48
        z = radius * math.sin(elev)
        rad = radius * math.cos(elev)
        row = []
        for s in range(segs):
            ang = (s / segs) * math.tau
            vertex.addData3(rad * math.cos(ang), rad * math.sin(ang), z)
            color.addData4(Vec4(cr, cg, cb, 1))
            row.append(r * segs + s)
        idx.append(row)
    tris = GeomTriangles(Geom.UHStatic)
    for r in range(rings):
        for s in range(segs):
            a = idx[r][s]
            b = idx[r][(s + 1) % segs]
            c = idx[r + 1][s]
            d = idx[r + 1][(s + 1) % segs]
            tris.addVertices(a, c, b)
            tris.addVertices(b, c, d)
    tris.closePrimitive()
    geom = Geom(vdata)
    geom.addPrimitive(tris)
    node = GeomNode("sky_dome")
    node.addGeom(geom)
    return node


def attach_sky(parent: NodePath) -> NodePath:
    pal = PALETTES["clear"]
    root = parent.attachNewNode(_sky_dome_build(16, 32, SKY_RADIUS, pal["zenith"], pal["horizon"]))
    root.setLightOff(1)
    root.setBin("background", 0)
    root.setDepthWrite(False)
    root.setTwoSided(True)
    return root


def rebuild_sky(parent: NodePath, old: NodePath, pal: dict) -> NodePath:
    pos = old.getPos()
    old.removeNode()
    root = parent.attachNewNode(_sky_dome_build(16, 32, SKY_RADIUS, pal["zenith"], pal["horizon"]))
    root.setLightOff(1)
    root.setBin("background", 0)
    root.setDepthWrite(False)
    root.setTwoSided(True)
    root.setPos(pos)
    return root


def apply_sun(render: NodePath, alight: AmbientLight, dlight: DirectionalLight) -> None:
    pal = PALETTES["clear"]
    alight.setColor(pal["ambient"])
    dlight.setDirection(Vec3(-0.45, -0.55, -0.85))
    dlight.setColor(pal["sun"])


def sun_direction(clock_h: float) -> Vec3:
    from .weather import sun_from_clock

    el, az = sun_from_clock(clock_h)
    er = math.radians(el)
    ar = math.radians(az)
    return Vec3(-math.cos(ar) * math.cos(er), -math.sin(ar) * math.cos(er), -max(0.04, math.sin(er)))


def attach_haze(render: NodePath, density: float) -> Fog:
    fog = Fog("blacksky_haze")
    fog.setColor(*PALETTES["clear"]["haze"])
    fog.setExpDensity(float(density))
    render.setFog(fog)
    return fog


def apply_lighting(
    render: NodePath,
    alight: AmbientLight,
    dlight: DirectionalLight,
    fog: Fog,
    atmos: AtmosphereState,
    base_density: float,
) -> dict:
    pal = palette_for(atmos)
    alight.setColor(pal["ambient"])
    dlight.setColor(pal["sun"])
    dlight.setDirection(sun_direction(atmos.clock_h))
    fog.setColor(*pal["haze"])
    extra = 0.00004 * (1.0 - min(40.0, atmos.visibility_km) / 40.0) + 0.00012 * atmos.storm
    fog.setExpDensity(float(base_density + extra))
    render.setFog(fog)
    return pal


def apply_atmosphere(
    render: NodePath,
    sky: NodePath,
    alight: AmbientLight,
    dlight: DirectionalLight,
    fog: Fog,
    atmos: AtmosphereState,
    base_density: float,
) -> NodePath:
    pal = apply_lighting(render, alight, dlight, fog, atmos, base_density)
    sky = rebuild_sky(render, sky, pal)
    return sky
