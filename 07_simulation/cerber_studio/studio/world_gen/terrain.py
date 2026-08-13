"""Heightfield tiles from WorldGraph. Physics uses NEAR+MID only."""

from __future__ import annotations

from panda3d.core import GeoMipTerrain, PNMImage

from .biomes import BiomeField
from .graph import WorldGraph

Z_SCALE = 220.0


def build_height_color(
    graph: WorldGraph,
    biomes: BiomeField,
    origin_x: float,
    origin_y: float,
    size_m: float,
    hf: int,
) -> tuple[PNMImage, PNMImage, float]:
    img = PNMImage(hf, hf)
    img.makeGrayscale()
    cmap = PNMImage(hf, hf)
    cmap.makeRgb()
    step = size_m / (hf - 1)
    for j in range(hf):
        for i in range(hf):
            wx = origin_x + i * step
            wy = origin_y + j * step
            h = graph.sample_height(wx, wy)
            if graph.airfield_mask(wx, wy):
                h = graph.airfields[0].elev if graph.airfields else 4.2
            img.setGray(i, j, max(0.0, min(1.0, h / Z_SCALE)))
            cr, cg, cb = biomes.color(wx, wy)
            cmap.setXel(i, j, cr, cg, cb)
    return img, cmap, step


def attach_geomip(
    parent,
    name: str,
    img: PNMImage,
    cmap: PNMImage,
    step: float,
    *,
    block: int = 16,
    near: float = 80.0,
    far: float = 280.0,
):
    terrain = GeoMipTerrain(name)
    terrain.setHeightfield(img)
    terrain.setColorMap(cmap)
    terrain.setBlockSize(block)
    terrain.setNear(near)
    terrain.setFar(far)
    terrain.setBruteforce(False)
    terrain.setBorderStitching(True)
    root = terrain.getRoot()
    root.reparentTo(parent)
    root.setSx(step)
    root.setSy(step)
    root.setSz(Z_SCALE)
    terrain.generate()
    return terrain
