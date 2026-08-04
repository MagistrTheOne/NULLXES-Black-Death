"""Procedural flying-wing meshes — visual presets, not CAD."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ursina import Entity, Mesh, Vec3, color


@dataclass(frozen=True)
class WingPreset:
    key: str
    title: str
    scale: float
    body_color: Any
    accent: Any
    max_speed: float
    turn_rate: float


def _c(r: int, g: int, b: int):
    return color.rgb(r / 255, g / 255, b / 255)


PRESETS: dict[str, WingPreset] = {
    "s800": WingPreset(
        key="s800",
        title="Reptile S800-class",
        scale=1.0,
        body_color=_c(35, 38, 42),
        accent=_c(220, 90, 40),
        max_speed=28.0,
        turn_rate=95.0,
    ),
    "ar_wing": WingPreset(
        key="ar_wing",
        title="AR Wing Pro-class",
        scale=1.35,
        body_color=_c(12, 12, 14),
        accent=_c(180, 30, 40),
        max_speed=34.0,
        turn_rate=75.0,
    ),
}


def _wing_mesh() -> Mesh:
    verts = [
        (0.0, 0.05, 1.2),
        (-1.4, 0.0, -0.9),
        (1.4, 0.0, -0.9),
        (0.0, 0.12, -0.2),
        (0.0, -0.08, -0.15),
        (-0.25, 0.02, -0.95),
        (0.25, 0.02, -0.95),
    ]
    tris = [
        0, 1, 3,
        0, 3, 2,
        0, 4, 1,
        0, 2, 4,
        1, 5, 3,
        2, 3, 6,
        1, 4, 5,
        2, 6, 4,
        3, 5, 6,
        4, 6, 5,
    ]
    return Mesh(vertices=verts, triangles=tris, mode="triangle")


def spawn_wing(preset: WingPreset, position: Vec3 | None = None) -> Entity:
    position = position or Vec3(0, 12, 0)
    root = Entity(name=f"ego_{preset.key}", position=position, scale=preset.scale)
    Entity(
        parent=root,
        model=_wing_mesh(),
        color=preset.body_color,
        double_sided=True,
    )
    Entity(
        parent=root,
        model="cube",
        color=preset.accent,
        scale=(0.15, 0.04, 0.35),
        position=(-1.25, 0.02, -0.75),
    )
    Entity(
        parent=root,
        model="cube",
        color=preset.accent,
        scale=(0.15, 0.04, 0.35),
        position=(1.25, 0.02, -0.75),
    )
    Entity(
        parent=root,
        model="cube",
        color=_c(60, 60, 65),
        scale=(0.18, 0.14, 0.45),
        position=(0, 0.02, -0.85),
    )
    return root


def spawn_target(position: Vec3 | None = None) -> Entity:
    position = position or Vec3(25, 18, 40)
    t = Entity(
        name="target_uav",
        model="cube",
        color=_c(255, 140, 40),
        scale=(0.9, 0.25, 1.1),
        position=position,
    )
    Entity(
        parent=t,
        model="cube",
        color=_c(40, 40, 40),
        scale=(1.8, 0.08, 0.35),
        position=(0, 0, 0),
    )
    return t
