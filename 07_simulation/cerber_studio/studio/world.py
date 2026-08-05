"""Procedural flying-wing scene — product visual models v1 (Panda3D Z-up)."""

from __future__ import annotations

import math

from panda3d.core import (
    Geom,
    GeomNode,
    GeomTriangles,
    GeomVertexData,
    GeomVertexFormat,
    GeomVertexWriter,
    NodePath,
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


def orbit_target(node: NodePath, phase: float) -> None:
    r = 28.0
    x = 20 + r * math.cos(phase)
    y = 50 + r * math.sin(phase)
    z = 18 + 3 * math.sin(phase * 2)
    node.setPos(x, y, z)
    node.setH(-math.degrees(phase) + 90)

