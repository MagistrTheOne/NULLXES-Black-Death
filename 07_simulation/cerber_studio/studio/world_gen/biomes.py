"""Biome masks from WorldGraph + local noise. Scatter reads these, not raw Perlin."""

from __future__ import annotations

from panda3d.core import PerlinNoise2

from .graph import WorldGraph


class BiomeField:
    def __init__(self, graph: WorldGraph) -> None:
        self.graph = graph
        s = graph.seed + graph.profile.seed_salt
        self._veg = PerlinNoise2(s * 0.01 + 8.0, s * 0.009 + 4.2)
        self._veg.setScale(90)
        self._rock = PerlinNoise2(s * 0.02 + 1.7, s * 0.013 + 3.3)
        self._rock.setScale(140)

    def veg(self, x: float, y: float) -> float:
        return float(self._veg.noise(x, y) * 0.5 + 0.5)

    def rock(self, x: float, y: float) -> float:
        return float(self._rock.noise(x, y) * 0.5 + 0.5)

    def kind(self, x: float, y: float) -> str:
        g = self.graph
        if g.airfield_mask(x, y) or g.river_mask(x, y, 28.0) or g.road_mask(x, y, 10.0):
            return "clear"
        if g.industrial_mask(x, y):
            return "industrial"
        if g.settlement_mask(x, y):
            return "town"
        sl = g.slope(x, y)
        if sl > 18.0 or self.rock(x, y) > 0.72:
            return "rock"
        if self.veg(x, y) > (1.0 - g.profile.forest_weight):
            return "forest"
        return "grass"

    def color(self, x: float, y: float) -> tuple[float, float, float]:
        k = self.kind(x, y)
        if k == "clear":
            if self.graph.airfield_mask(x, y):
                return (0.28, 0.29, 0.30)
            if self.graph.river_mask(x, y, 28.0):
                return (0.18, 0.32, 0.38)
            return (0.22, 0.22, 0.22)
        if k == "industrial":
            return (0.34, 0.32, 0.28)
        if k == "town":
            return (0.30, 0.28, 0.24)
        if k == "rock":
            return (0.38, 0.36, 0.32)
        if k == "forest":
            return (0.16, 0.28, 0.14)
        return (0.22, 0.32, 0.16)
