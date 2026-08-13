"""Procedural flying-wing scene — product visual models v1 (Panda3D Z-up)."""

from __future__ import annotations

import math

from panda3d.core import (
    AmbientLight,
    DirectionalLight,
    Geom,
    GeomNode,
    GeomTriangles,
    GeomVertexData,
    GeomVertexFormat,
    GeomVertexWriter,
    NodePath,
    PointLight,
    Vec4,
)

from .dynamics import WingParams


def _make_wing_geom(color: tuple[float, float, float]) -> GeomNode:
    fmt = GeomVertexFormat.getV3c4()
    vdata = GeomVertexData("wing", fmt, Geom.UHStatic)
    vertex = GeomVertexWriter(vdata, "vertex")
    color_w = GeomVertexWriter(vdata, "color")
    # local: +Y nose, +Z up, +X right
    verts = [
        (0.0, 1.2, 0.05),
        (-1.4, -0.9, 0.0),
        (1.4, -0.9, 0.0),
        (0.0, -0.2, 0.12),
        (0.0, -0.15, -0.08),
        (-0.25, -0.95, 0.02),
        (0.25, -0.95, 0.02),
    ]
    c = Vec4(color[0], color[1], color[2], 1)
    for v in verts:
        vertex.addData3(*v)
        color_w.addData4(c)
    tris = GeomTriangles(Geom.UHStatic)
    for a, b, c_i in (
        (0, 1, 3),
        (0, 3, 2),
        (0, 4, 1),
        (0, 2, 4),
        (1, 5, 3),
        (2, 3, 6),
        (1, 4, 5),
        (2, 6, 4),
        (3, 5, 6),
        (4, 6, 5),
    ):
        tris.addVertices(a, b, c_i)
    tris.closePrimitive()
    geom = Geom(vdata)
    geom.addPrimitive(tris)
    node = GeomNode("wing_mesh")
    node.addGeom(geom)
    return node


def _box(color: tuple[float, float, float]) -> GeomNode:
    fmt = GeomVertexFormat.getV3c4()
    vdata = GeomVertexData("box", fmt, Geom.UHStatic)
    vertex = GeomVertexWriter(vdata, "vertex")
    color_w = GeomVertexWriter(vdata, "color")
    corners = [
        (-1, -1, -1),
        (1, -1, -1),
        (1, 1, -1),
        (-1, 1, -1),
        (-1, -1, 1),
        (1, -1, 1),
        (1, 1, 1),
        (-1, 1, 1),
    ]
    c = Vec4(color[0], color[1], color[2], 1)
    for p in corners:
        vertex.addData3(*p)
        color_w.addData4(c)
    faces = (
        (0, 1, 2, 3),
        (4, 5, 6, 7),
        (0, 1, 5, 4),
        (2, 3, 7, 6),
        (0, 3, 7, 4),
        (1, 2, 6, 5),
    )
    tris = GeomTriangles(Geom.UHStatic)
    for a, b, c_i, d in faces:
        tris.addVertices(a, b, c_i)
        tris.addVertices(a, c_i, d)
    tris.closePrimitive()
    geom = Geom(vdata)
    geom.addPrimitive(tris)
    node = GeomNode("box")
    node.addGeom(geom)
    return node


def attach_wing(parent: NodePath, params: WingParams) -> NodePath:
    root = parent.attachNewNode(f"ego_{params.key}")
    root.setScale(params.scale)
    mesh = root.attachNewNode(_make_wing_geom(params.color_rgb))
    mesh.setTwoSided(True)
    tip_l = root.attachNewNode("tip_l")
    tip_l.setPos(-1.25, -0.75, 0.02)
    tip_l.setScale(0.08, 0.18, 0.02)
    tip_l.attachNewNode(_box(params.accent_rgb))
    tip_r = root.attachNewNode("tip_r")
    tip_r.setPos(1.25, -0.75, 0.02)
    tip_r.setScale(0.08, 0.18, 0.02)
    tip_r.attachNewNode(_box(params.accent_rgb))
    nacelle = root.attachNewNode("nacelle")
    nacelle.setPos(0, -0.85, 0.02)
    nacelle.setScale(0.09, 0.22, 0.07)
    nacelle.attachNewNode(_box((0.25, 0.25, 0.27)))
    return root


def attach_target(parent: NodePath) -> NodePath:
    t = parent.attachNewNode("target_uav")
    body = t.attachNewNode(_box((1.0, 0.55, 0.15)))
    body.setScale(0.45, 0.55, 0.12)
    wing = t.attachNewNode(_box((0.15, 0.15, 0.15)))
    wing.setScale(0.9, 0.18, 0.04)
    return t


def attach_ground(parent: NodePath) -> None:
    ground = parent.attachNewNode(_box((0.18, 0.22, 0.16)))
    ground.setScale(200, 200, 0.05)
    ground.setPos(0, 0, 0)
    strip = parent.attachNewNode(_box((0.25, 0.25, 0.28)))
    strip.setScale(6, 60, 0.06)
    strip.setPos(0, 40, 0.06)


def orbit_target(node: NodePath, phase: float, *, behaviour: str = "simple") -> None:
    if behaviour == "static":
        node.setPos(24.0, 48.0, 18.0)
        node.setH(90.0)
        return
    speed = 0.55 if behaviour == "evasive" else 0.35
    r = 36.0 if behaviour == "evasive" else 28.0
    z_amp = 6.0 if behaviour == "evasive" else 3.0
    x = 20 + r * math.cos(phase * (1.4 if behaviour == "evasive" else 1.0))
    y = 50 + r * math.sin(phase)
    z = 18 + z_amp * math.sin(phase * 2)
    node.setPos(x, y, z)
    node.setH(-math.degrees(phase * speed / 0.35) + 90)


def attach_hangar(parent: NodePath) -> NodePath:
    root = parent.attachNewNode("hangar")
    floor = root.attachNewNode(_box((0.22, 0.22, 0.24)))
    floor.setScale(10.0, 8.0, 0.04)
    floor.setPos(0, 0.6, 0)
    pedestal = root.attachNewNode(_box((0.32, 0.32, 0.34)))
    pedestal.setScale(1.7, 1.7, 0.08)
    pedestal.setPos(0, 0, 0.10)
    back = root.attachNewNode(_box((0.09, 0.09, 0.10)))
    back.setScale(11.0, 0.18, 3.6)
    back.setPos(0, 6.4, 3.4)
    panel_l = root.attachNewNode(_box((0.14, 0.14, 0.15)))
    panel_l.setScale(0.12, 3.2, 2.4)
    panel_l.setPos(-7.4, 2.2, 2.6)
    panel_r = root.attachNewNode(_box((0.14, 0.14, 0.15)))
    panel_r.setScale(0.12, 3.2, 2.4)
    panel_r.setPos(7.4, 2.2, 2.6)
    beam = root.attachNewNode(_box((0.18, 0.18, 0.19)))
    beam.setScale(8.5, 0.08, 0.08)
    beam.setPos(0, 5.8, 5.4)
    anchor = root.attachNewNode("preview_anchor")
    anchor.setPos(0.0, 0.0, 0.22)
    key = PointLight("hangar_key")
    key.setColor((1.15, 1.08, 1.0, 1))
    key.setAttenuation((1.0, 0.012, 0.001))
    kn = root.attachNewNode(key)
    kn.setPos(3.2, -4.5, 5.4)
    root.setLight(kn)
    fill = PointLight("hangar_fill")
    fill.setColor((0.42, 0.46, 0.52, 1))
    fill.setAttenuation((1.0, 0.02, 0.002))
    fn = root.attachNewNode(fill)
    fn.setPos(-4.0, 3.5, 3.8)
    root.setLight(fn)
    rim = DirectionalLight("hangar_rim")
    rim.setDirection((-0.2, 0.85, -0.25))
    rim.setColor((0.55, 0.58, 0.62, 1))
    rn = root.attachNewNode(rim)
    root.setLight(rn)
    amb = AmbientLight("hangar_amb")
    amb.setColor((0.38, 0.40, 0.44, 1))
    an = root.attachNewNode(amb)
    root.setLight(an)
    return root

