"""Roads as strips from WorldGraph polylines."""

from __future__ import annotations

from panda3d.core import NodePath

from .geom import polyline_strips
from .graph import WorldGraph


def build_roads(parent: NodePath, graph: WorldGraph, lod: str) -> None:
    width = graph.profile.road_width if lod == "near" else graph.profile.road_width * 1.4
    polyline_strips(parent, _flatten(graph.roads), width=width, height_fn=graph.sample_height, color=(0.16, 0.16, 0.16), z_off=0.14)


def _flatten(lines: list[list[tuple[float, float]]]) -> list[tuple[float, float]]:
    out: list[tuple[float, float]] = []
    for line in lines:
        if out and line:
            out.append(out[-1])
        out.extend(line)
    return out


def build_road_lines(parent: NodePath, graph: WorldGraph, lod: str) -> None:
    width = graph.profile.road_width if lod == "near" else graph.profile.road_width * 1.35
    color = (0.16, 0.16, 0.16)
    for line in graph.roads:
        polyline_strips(parent, line, width=width, height_fn=graph.sample_height, color=color, z_off=0.14)
