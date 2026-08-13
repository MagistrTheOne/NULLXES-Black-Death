"""Prop placement from biome/graph masks. Never scatter on raw Perlin alone."""

from __future__ import annotations

from panda3d.core import NodePath

from .biomes import BiomeField
from .geom import box, cone
from .graph import WorldGraph, sector_seed


def scatter_sector(
    props: NodePath,
    graph: WorldGraph,
    biomes: BiomeField,
    ox: float,
    oy: float,
    size_m: float,
    sx: int,
    sy: int,
    packs: dict,
    density: str,
) -> None:
    if density == "none":
        return
    step = 56.0 if density == "full" else 110.0
    rng = sector_seed(graph.seed, graph.region_id, sx, sy)
    n = max(1, int(size_m / step))
    tree_g = cone((0.12, 0.22, 0.11))
    trunk_g = box((0.28, 0.20, 0.12))
    rock_g = box((0.40, 0.38, 0.34))
    for iy in range(n):
        for ix in range(n):
            jitter = ((ix * 17 + iy * 31 + rng) % 100) / 100.0
            wx = ox + (ix + 0.35 + jitter * 0.3) * step
            wy = oy + (iy + 0.4 + ((ix * 13 + rng) % 50) / 80.0) * step
            kind = biomes.kind(wx, wy)
            if kind in ("clear", "town", "industrial"):
                continue
            h = graph.sample_height(wx, wy)
            local_x = wx - ox
            local_y = wy - oy
            cell = (ix + iy + rng) % 7
            if kind == "forest" and cell <= (2 if density == "full" else 1):
                if packs.get("tree") is not None:
                    node = packs["tree"].copyTo(props)
                    node.setPos(local_x, local_y, h)
                    node.setScale(1.6 + jitter)
                else:
                    trunk = props.attachNewNode(trunk_g)
                    trunk.setPos(local_x, local_y, h + 0.7)
                    trunk.setScale(0.18, 0.18, 0.7)
                    crown = props.attachNewNode(tree_g)
                    crown.setPos(local_x, local_y, h + 1.1)
                    crown.setScale(1.8 + jitter, 1.8 + jitter, 3.4 + jitter * 2)
            elif kind == "rock" and cell == 0:
                if packs.get("rock") is not None:
                    node = packs["rock"].copyTo(props)
                    node.setPos(local_x, local_y, h)
                    node.setScale(0.9 + jitter * 0.4)
                else:
                    rock = props.attachNewNode(rock_g)
                    rock.setPos(local_x, local_y, h + 0.4)
                    rock.setScale(0.8 + jitter, 0.6, 0.45)
