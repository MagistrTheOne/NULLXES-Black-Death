"""River surfaces from WorldGraph polylines."""

from __future__ import annotations

from panda3d.core import NodePath

from .geom import polyline_strips
from .graph import WorldGraph


def build_rivers(parent: NodePath, graph: WorldGraph, lod: str) -> None:
    width = 22.0 if lod == "near" else 28.0 if lod == "mid" else 40.0
    for line in graph.rivers:
        polyline_strips(
            parent,
            line,
            width=width,
            height_fn=lambda x, y: graph.sample_height(x, y) - 0.4,
            color=(0.12, 0.28, 0.34),
            z_off=0.35,
        )
