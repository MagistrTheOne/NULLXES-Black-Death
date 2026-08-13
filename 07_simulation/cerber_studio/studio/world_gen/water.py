"""Water surfaces: coast plane + river sheets. Not terrain vertex paint."""

from __future__ import annotations

import math

from panda3d.core import NodePath, TransparencyAttrib

from .geom import box
from .graph import WorldGraph


def attach_water_plane(
    parent: NodePath,
    *,
    origin: tuple[float, float],
    size: float,
    z: float,
    color: tuple[float, float, float] = (0.10, 0.22, 0.28),
) -> NodePath:
    sheet = parent.attachNewNode("water_plane")
    node = sheet.attachNewNode(box(color))
    node.setScale(size * 0.5, size * 0.5, 0.08)
    node.setPos(origin[0], origin[1], z)
    sheet.setTransparency(TransparencyAttrib.MAlpha)
    sheet.setColorScale(color[0], color[1], color[2], 0.82)
    sheet.setLightOff(0)
    return sheet


def build_rivers(parent: NodePath, graph: WorldGraph, lod: str) -> None:
    width = 28.0 if lod == "near" else 36.0 if lod == "mid" else 48.0
    color = graph.profile.water_rgb
    mesh = box(color)
    z_water = graph.profile.water_level if graph.profile.water_enabled else None
    for line in graph.rivers:
        if len(line) < 2:
            continue
        for i in range(len(line) - 1):
            x0, y0 = line[i]
            x1, y1 = line[i + 1]
            dx, dy = x1 - x0, y1 - y0
            length = math.hypot(dx, dy)
            if length < 2.0:
                continue
            mx, my = (x0 + x1) * 0.5, (y0 + y1) * 0.5
            terrain_z = min(graph.sample_height(x0, y0), graph.sample_height(x1, y1), graph.sample_height(mx, my))
            z = (z_water if z_water is not None else terrain_z) - 0.15
            z = min(z, terrain_z - 0.2)
            n = parent.attachNewNode(mesh)
            n.setPos(mx, my, z)
            n.setH(math.degrees(math.atan2(dx, dy)))
            n.setScale(width * 0.5, length * 0.5, 0.18)
            n.setTransparency(TransparencyAttrib.MAlpha)
            n.setColorScale(color[0], color[1], color[2], 0.88)
