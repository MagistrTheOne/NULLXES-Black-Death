"""Biome masks from WorldGraph + local noise. Scatter reads these, not raw Perlin."""

from __future__ import annotations

from panda3d.core import PerlinNoise2

from .graph import WorldGraph


def _lerp(a: tuple[float, float, float], b: tuple[float, float, float], t: float) -> tuple[float, float, float]:
    t = max(0.0, min(1.0, t))
    return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t)


class BiomeField:
    def __init__(self, graph: WorldGraph) -> None:
        self.graph = graph
        s = graph.seed + graph.profile.seed_salt
        self._veg = PerlinNoise2(s * 0.01 + 8.0, s * 0.009 + 4.2)
        self._veg.setScale(90)
        self._rock = PerlinNoise2(s * 0.02 + 1.7, s * 0.013 + 3.3)
        self._rock.setScale(140)
        self._mask = PerlinNoise2(s * 0.015 + 4.4, s * 0.018 + 2.1)
        self._mask.setScale(220)

    def veg(self, x: float, y: float) -> float:
        return float(self._veg.noise(x, y) * 0.5 + 0.5)

    def rock(self, x: float, y: float) -> float:
        return float(self._rock.noise(x, y) * 0.5 + 0.5)

    def mask(self, x: float, y: float) -> float:
        return float(self._mask.noise(x, y) * 0.5 + 0.5)

    def kind(self, x: float, y: float) -> str:
        g = self.graph
        p = g.profile
        if p.water_enabled and g.sample_height(x, y) <= p.water_level + 0.35:
            return "water"
        if g.airfield_mask(x, y) or g.river_mask(x, y, 28.0) or g.road_mask(x, y, 10.0):
            return "clear"
        if g.industrial_mask(x, y):
            return "industrial"
        if g.settlement_mask(x, y):
            return "town"
        sl = g.slope(x, y)
        h = g.sample_height(x, y)
        mid = p.material_id
        if sl > 16.0 or self.rock(x, y) > (0.62 if mid == "arctic" else 0.72):
            return "rock"
        if h >= p.snow_alt or (mid == "arctic" and h >= p.snow_alt * 0.45):
            return "snow"
        if mid == "arctic":
            return "tundra"
        if mid == "arid":
            return "sand"
        if self.veg(x, y) > (1.0 - g.profile.forest_weight):
            return "forest"
        return "grass"

    def color(self, x: float, y: float, *, lod: str = "near") -> tuple[float, float, float]:
        g = self.graph
        p = g.profile
        k = self.kind(x, y)
        h = g.sample_height(x, y)
        sl = g.slope(x, y)
        n = self.mask(x, y)
        if k == "water":
            c = p.water_rgb
        elif k == "clear":
            if g.airfield_mask(x, y):
                c = (0.28, 0.29, 0.30)
            elif g.river_mask(x, y, 28.0):
                c = p.water_rgb
            else:
                c = (0.22, 0.22, 0.22)
        elif k == "industrial":
            c = (0.34, 0.32, 0.28)
        elif k == "town":
            c = (0.30, 0.28, 0.24)
        elif k == "rock":
            c = _lerp(p.slope_rgb, p.highland_rgb, min(1.0, sl / 40.0))
        elif k == "snow":
            c = _lerp(p.highland_rgb, p.snow_rgb, 0.55 + n * 0.45)
        elif k == "tundra":
            dirt = (0.42, 0.40, 0.36)
            c = _lerp(p.lowland_rgb, dirt, n * 0.35)
            if sl > 8.0:
                c = _lerp(c, p.slope_rgb, min(1.0, (sl - 8.0) / 14.0))
        elif k == "sand":
            c = _lerp(p.lowland_rgb, p.highland_rgb, n * 0.4)
        elif k == "forest":
            c = (
                p.lowland_rgb[0] * 0.72,
                p.lowland_rgb[1] * 0.88,
                p.lowland_rgb[2] * 0.70,
            )
        else:
            c = p.lowland_rgb
            if sl > 10.0:
                c = _lerp(c, p.slope_rgb, min(1.0, (sl - 10.0) / 18.0))
            if h > p.snow_alt * 0.72:
                c = _lerp(c, p.snow_rgb, min(1.0, (h - p.snow_alt * 0.72) / 40.0))
        if p.water_enabled and h < p.water_level + 3.5 and k != "water":
            sand = (0.62, 0.56, 0.42)
            c = _lerp(sand, c, min(1.0, (h - p.water_level) / 3.5))
        if lod == "far":
            haze = p.haze_rgb or (0.70, 0.76, 0.82)
            c = _lerp(c, haze, 0.62)
        elif lod == "mid":
            haze = p.haze_rgb or (0.70, 0.76, 0.82)
            c = _lerp(c, haze, 0.22)
        return c
