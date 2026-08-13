"""Shared procedural geoms for world_gen. No GLB required."""

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
    Vec3,
    Vec4,
)


def box(color: tuple[float, float, float]) -> GeomNode:
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


def cone(color: tuple[float, float, float], sides: int = 8) -> GeomNode:
    fmt = GeomVertexFormat.getV3c4()
    vdata = GeomVertexData("cone", fmt, Geom.UHStatic)
    vertex = GeomVertexWriter(vdata, "vertex")
    color_w = GeomVertexWriter(vdata, "color")
    c = Vec4(*color, 1)
    vertex.addData3(0, 0, 1)
    color_w.addData4(c)
    for i in range(sides):
        ang = i / sides * math.tau
        vertex.addData3(math.cos(ang), math.sin(ang), 0)
        color_w.addData4(c)
    tris = GeomTriangles(Geom.UHStatic)
    for i in range(sides):
        tris.addVertices(0, 1 + i, 1 + ((i + 1) % sides))
    tris.closePrimitive()
    geom = Geom(vdata)
    geom.addPrimitive(tris)
    node = GeomNode("cone")
    node.addGeom(geom)
    return node


def place_box(parent: NodePath, color: tuple[float, float, float], pos, scale) -> NodePath:
    n = parent.attachNewNode(box(color))
    n.setPos(*pos)
    n.setScale(*scale)
    return n


def polyline_strips(
    parent: NodePath,
    points: list[tuple[float, float]],
    *,
    width: float,
    height_fn,
    color: tuple[float, float, float],
    z_off: float = 0.12,
) -> None:
    if len(points) < 2:
        return
    mesh = box(color)
    for i in range(len(points) - 1):
        x0, y0 = points[i]
        x1, y1 = points[i + 1]
        dx, dy = x1 - x0, y1 - y0
        length = math.hypot(dx, dy)
        if length < 1.0:
            continue
        yaw = math.degrees(math.atan2(dx, dy))
        mx, my = (x0 + x1) * 0.5, (y0 + y1) * 0.5
        z = height_fn(mx, my) + z_off
        n = parent.attachNewNode(mesh)
        n.setPos(mx, my, z)
        n.setH(yaw)
        n.setScale(width * 0.5, length * 0.5, z_off)
