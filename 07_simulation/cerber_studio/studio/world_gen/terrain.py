"""Heightfield tiles from WorldGraph. Physics uses NEAR+MID only."""

from __future__ import annotations

from panda3d.core import GeoMipTerrain, PNMImage, SamplerState, Texture

from .biomes import BiomeField
from .graph import WorldGraph

Z_SCALE = 220.0


def sector_world_xy(origin_x: float, origin_y: float, size_m: float, hf: int, i: int, j: int) -> tuple[float, float]:
    step = size_m / max(1, hf - 1)
    return origin_x + i * step, origin_y + j * step


def build_height_color(
    graph: WorldGraph,
    biomes: BiomeField,
    origin_x: float,
    origin_y: float,
    size_m: float,
    hf: int,
    *,
    lod: str = "near",
) -> tuple[PNMImage, PNMImage, float]:
    img = PNMImage(hf, hf)
    img.makeGrayscale()
    cmap = PNMImage(hf, hf)
    cmap.makeRgb()
    step = size_m / max(1, hf - 1)
    for j in range(hf):
        for i in range(hf):
            wx = origin_x + i * step
            wy = origin_y + j * step
            h = graph.sample_height(wx, wy)
            if graph.airfield_mask(wx, wy):
                h = graph.airfields[0].elev if graph.airfields else 4.2
            img.setGray(i, j, max(0.0, min(1.0, h / Z_SCALE)))
            cr, cg, cb = biomes.color(wx, wy, lod=lod)
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
    cmap_tex = Texture(f"{name}_cmap")
    cmap_tex.load(cmap)
    cmap_tex.setWrapU(SamplerState.WM_clamp)
    cmap_tex.setWrapV(SamplerState.WM_clamp)
    cmap_tex.setMinfilter(SamplerState.FT_linear)
    cmap_tex.setMagfilter(SamplerState.FT_linear)
    root.setTexture(cmap_tex)
    root.setLightOff(1)
    return terrain
