"""Aircraft visual animation: GLB clips if present, else manifest/procedural rotors."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from panda3d.core import AnimControlCollection, NodePath, autoBind

from .definition import AircraftDefinition

log = logging.getLogger("cerber_studio.aircraft")

_NAME_HINTS = ("rotor", "propeller", "prop_", "blade", "spinner")
_PRESENTATIONAL = ("explod", "step_by_step", "disassemble", "teardown", "breakdown")
MAX_VISUAL_DPS = 2160.0


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
    collection: AnimControlCollection | None = None
    clip: object | None = None
    clip_name: str = ""

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
        if self.clip is not None:
            self._drive_clip()
            return
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

    def _drive_clip(self) -> None:
        ctrl = self.clip
        if ctrl is None:
            return
        try:
            if self.hangar or self.rpm <= 0.0:
                if ctrl.isPlaying():
                    ctrl.stop()
                ctrl.pose(0)
                return
            ctrl.setPlayRate(0.45 + 0.55 * self.rpm)
            if not ctrl.isPlaying():
                ctrl.loop(True)
        except Exception as exc:  # noqa: BLE001
            log.debug("clip drive failed: %s", exc)


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


def _is_presentational(name: str) -> bool:
    low = name.lower()
    return any(token in low for token in _PRESENTATIONAL)


def _bind_anims(root: NodePath) -> tuple[AnimControlCollection | None, list[str]]:
    collection = AnimControlCollection()
    try:
        autoBind(root.node(), collection, ~0)
    except Exception as exc:  # noqa: BLE001
        log.warning("autoBind failed: %s", exc)
        return None, _clip_names(root)
    names: list[str] = []
    count = int(collection.get_num_anims())
    for i in range(count):
        names.append(str(collection.get_anim_name(i)))
    if not names:
        names = _clip_names(root)
    return (collection if count else None), names


def _select_clip(collection: AnimControlCollection | None, names: list[str], preferred: str):
    if collection is None or collection.get_num_anims() == 0:
        return None, ""
    order: list[str] = []
    if preferred:
        order.append(preferred)
    for name in names:
        if name not in order and not _is_presentational(name):
            order.append(name)
    for name in names:
        if name not in order:
            order.append(name)
    for name in order:
        ctrl = collection.find_anim(name)
        if ctrl:
            return ctrl, name
    return collection.get_anim(0), names[0] if names else ""


def _find_node(root: NodePath, spec: str) -> NodePath:
    found = root.find(f"**/{spec}")
    if not found.isEmpty():
        return found
    return root.find(f"**/{spec}*")


def discover_and_bind(root: NodePath, defn: AircraftDefinition) -> VisualAnimator:
    nodes = _walk(root)
    collection, clips = _bind_anims(root)
    clip, clip_name = _select_clip(collection, clips, defn.animation.flight_clip)
    node_names = [n.getName() for n in nodes if n.getName()]
    log.info("AIRCRAFT: %s", defn.id)
    log.info("animations: %s", ", ".join(clips) if clips else "(none)")
    if clip_name:
        log.info("flight_clip: %s", clip_name)
    hinted = [n for n in node_names if any(h in n.lower() for h in _NAME_HINTS)]
    log.info("nodes: %s", ", ".join(hinted[:24]) if hinted else "(no rotor/prop names)")

    bound: list[BoundRotor] = []
    if clip is None:
        specs = list(defn.animation.rotors) + list(defn.animation.propellers)
        if specs:
            for spec in specs:
                found = _find_node(root, spec.node)
                if found.isEmpty():
                    continue
                bound.append(BoundRotor(found, spec.axis, float(spec.direction)))
        else:
            for node in nodes:
                name = node.getName().lower()
                if not any(h in name for h in _NAME_HINTS):
                    continue
                if "_correction" in name or "motor_base" in name or "bolt" in name:
                    continue
                bound.append(BoundRotor(node, "Z", 1.0 if len(bound) % 2 == 0 else -1.0))

    animator = VisualAnimator(
        rotors=bound,
        clips=clips,
        discovered=True,
        collection=collection,
        clip=clip,
        clip_name=clip_name,
        hangar=True,
    )
    animator.step(0.0)
    return animator
