"""Demo mission YAML — not ArduPlane mission protocol."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from ..config.paths import MISSIONS_DIR

log = logging.getLogger("cerber_studio.missions")


@dataclass
class Waypoint:
    x: float
    y: float
    z: float
    radius_m: float = 20.0
    kind: str = "goto_xyz"


@dataclass
class MissionDefinition:
    id: str
    name: str
    type: str
    environment: str
    target: bool
    duration_s: int
    description: str
    waypoints: list[Waypoint] = field(default_factory=list)
    demo: bool = True


def _wp(raw: dict) -> Waypoint:
    return Waypoint(
        x=float(raw.get("x", 0.0)),
        y=float(raw.get("y", 80.0)),
        z=float(raw.get("z", 30.0)),
        radius_m=float(raw.get("radius_m", 20.0)),
        kind=str(raw.get("kind", "goto_xyz")),
    )


def _from_yaml(path: Path) -> MissionDefinition | None:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception as exc:  # noqa: BLE001
        log.warning("invalid mission YAML %s: %s", path.name, exc)
        return None
    ident = str(data.get("id") or path.stem)
    wps = [_wp(w) for w in data.get("waypoints") or [] if isinstance(w, dict)]
    return MissionDefinition(
        id=ident,
        name=str(data.get("name") or ident.replace("_", " ").upper()),
        type=str(data.get("type") or "free_flight"),
        environment=str(data.get("environment") or "open"),
        target=bool(data.get("target", False)),
        duration_s=int(data.get("duration_s") or data.get("timeout_s") or 0),
        description=str(data.get("description") or ""),
        waypoints=wps,
        demo=bool(data.get("demo", True)),
    )


class MissionRegistry:
    def __init__(self) -> None:
        self.items: list[MissionDefinition] = []

    def scan(self) -> list[MissionDefinition]:
        found: dict[str, MissionDefinition] = {}
        if MISSIONS_DIR.is_dir():
            for path in sorted(MISSIONS_DIR.glob("*.yaml")):
                mission = _from_yaml(path)
                if mission is None:
                    continue
                found[mission.id] = mission
        if not found:
            found["free_flight"] = MissionDefinition(
                id="free_flight",
                name="FREE FLIGHT",
                type="free_flight",
                environment="open",
                target=False,
                duration_s=0,
                description="Open airspace. No assigned target.",
            )
        self.items = list(found.values())
        return self.items

    def get(self, ident: str) -> MissionDefinition | None:
        for item in self.items:
            if item.id == ident:
                return item
        return None

    def get_or_first(self, ident: str) -> MissionDefinition:
        hit = self.get(ident)
        if hit is not None:
            return hit
        return self.items[0]
