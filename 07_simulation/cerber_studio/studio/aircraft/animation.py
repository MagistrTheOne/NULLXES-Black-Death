"""Aircraft visual animation: GLB clips if present, else manifest/procedural rotors."""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field

from panda3d.core import NodePath, Vec3

from .definition import AircraftDefinition, RotorSpec

log = logging.getLogger("cerber_studio.aircraft")

_NAME_HINTS = ("rotor", "propeller", "prop_", "blade", "spinner")
MAX_VISUAL_DPS = 2160.0
AXIS = {"X": Vec3(1, 0, 0), "Y": Vec3(0, 1, 0), "Z": Vec3(0, 0, 1)}


@dataclass
class BoundRotor:
    node: NodePath
    axis: str
    direction: float
    angle: float = 0.0


@dataclass
class VisualAnimator:
    rotors: list[BoundRotor] = field(default_factory=list)
    clips: list[str] = field(default_factory=list)
    rpm: float = 0.0
    hangar: bool = True
    discovered: bool = False

    def set_throttle(self, throttle: float) -> None:
        thr = max(0.0, min(1.0, float(throttle)))
        if self.hangar:
            self.rpm = 0.0
            return
        if thr < 0.04:
            self.rpm = 0.0
        elif thr < 0.2:
            self.rpm = 0.12 * (thr / 0.2)
        else:
            self.rpm = 0.12 + 0.88 * ((thr - 0.2) / 0.8)

    def step(self, dt: float) -> None:
        if not self.rotors or self.rpm <= 0.0:
            return
        dps = min(MAX_VISUAL_DPS, 80.0 + self.rpm * (MAX_VISUAL_DPS - 80.0))
        for rotor in self.rotors:
            rotor.angle = (rotor.angle + dps * rotor.direction * dt) % 360.0
            axis = (rotor.axis or "Z").upper()
            if axis == "X":
                rotor.node.setR(rotor.angle)
            elif axis == "Y":
                rotor.node.setP(rotor.angle)
            else:
                rotor.node.setH(rotor.angle)


def _walk(node: NodePath) -> list[NodePath]:
    out = [node]
    try:
        children = node.getChildren()
    except Exception:
        return out
    for child in children:
        out.extend(_walk(child))
    return out


def _clip_names(node: NodePath) -> list[str]:
    names: list[str] = []
    try:
        bundled = node.findAllMatches("**/+AnimBundleNode")
        for i in range(bundled.getNumPaths()):
            names.append(bundled.getPath(i).getName())
    except Exception:
        pass
    return names


def discover_and_bind(root: NodePath, defn: AircraftDefinition) -> VisualAnimator:
    nodes = _walk(root)
    clips = _clip_names(root)
    node_names = [n.getName() for n in nodes if n.getName()]
    log.info("AIRCRAFT: %s", defn.id)
    log.info("animations: %s", ", ".join(clips) if clips else "(none)")
    hinted = [n for n in node_names if any(h in n.lower() for h in _NAME_HINTS)]
    log.info("nodes: %s", ", ".join(hinted[:24]) if hinted else "(no rotor/prop names)")

    specs = list(defn.animation.rotors) + list(defn.animation.propellers)
    bound: list[BoundRotor] = []
    if specs:
        for spec in specs:
            found = root.find(f"**/{spec.node}")
            if found.isEmpty():
                continue
            bound.append(BoundRotor(found, spec.axis, float(spec.direction)))
    else:
        for node in nodes:
            name = node.getName().lower()
            if not any(h in name for h in _NAME_HINTS):
                continue
            bound.append(BoundRotor(node, "Z", 1.0 if len(bound) % 2 == 0 else -1.0))
    return VisualAnimator(rotors=bound, clips=clips, discovered=True)
