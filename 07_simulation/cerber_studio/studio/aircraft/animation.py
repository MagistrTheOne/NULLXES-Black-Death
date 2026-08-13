"""Aircraft visual animation: GLB flight clips if present, else manifest/procedural rotors."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from panda3d.core import AnimControlCollection, NodePath, autoBind

from .definition import AircraftDefinition, ControlSurfaceSpec, RotorSpec

log = logging.getLogger("cerber_studio.aircraft")

_NAME_HINTS = ("rotor", "propeller", "propellor", "prop_", "blade", "spinner", "fan")
_SKIP_NODE = (
    "_correction",
    "_lambert",
    "motor_base",
    "bolt",
    "nut",
    "cap",
    "fitting",
    "screw",
)
_PRESENTATIONAL = ("explod", "step_by_step", "disassemble", "teardown", "breakdown")
_FLIGHT_CLIP = ("hover", "fly", "idle", "spin", "rotor", "prop", "loop", "run")
MAX_VISUAL_DPS = 2160.0
SURFACE_MAX = 22.0


@dataclass
class BoundRotor:
    node: NodePath
    axis: str
    direction: float
    angle: float = 0.0
    rest_hpr: tuple[float, float, float] = (0.0, 0.0, 0.0)


@dataclass
class BoundSurface:
    node: NodePath
    source: str
    gain: float
    axis: str
    max_deg: float
    rest_hpr: tuple[float, float, float] = (0.0, 0.0, 0.0)


@dataclass
class VisualAnimator:
    rotors: list[BoundRotor] = field(default_factory=list)
    surfaces: list[BoundSurface] = field(default_factory=list)
    clips: list[str] = field(default_factory=list)
    rpm: float = 0.0
    hangar: bool = True
    discovered: bool = False
    collection: AnimControlCollection | None = None
    clip: object | None = None
    clip_name: str = ""
    pitch_cmd: float = 0.0
    roll_cmd: float = 0.0
    yaw_cmd: float = 0.0

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

    def set_controls(self, pitch: float, roll: float, yaw: float) -> None:
        if self.hangar:
            self.pitch_cmd = 0.0
            self.roll_cmd = 0.0
            self.yaw_cmd = 0.0
            return
        self.pitch_cmd = max(-1.0, min(1.0, float(pitch)))
        self.roll_cmd = max(-1.0, min(1.0, float(roll)))
        self.yaw_cmd = max(-1.0, min(1.0, float(yaw)))

    def step(self, dt: float) -> None:
        if self.clip is not None:
            self._drive_clip()
        elif self.rotors:
            self._drive_rotors(dt)
        self._drive_surfaces()

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

    def _drive_rotors(self, dt: float) -> None:
        if self.hangar or self.rpm <= 0.0:
            for rotor in self.rotors:
                _set_axis(rotor.node, rotor.axis, rotor.rest_hpr, 0.0)
            return
        dps = min(MAX_VISUAL_DPS, 80.0 + self.rpm * (MAX_VISUAL_DPS - 80.0))
        for rotor in self.rotors:
            rotor.angle = (rotor.angle + dps * rotor.direction * dt) % 360.0
            _set_axis(rotor.node, rotor.axis, rotor.rest_hpr, rotor.angle)

    def _drive_surfaces(self) -> None:
        for surface in self.surfaces:
            cmd = 0.0
            if not self.hangar:
                src = surface.source.lower()
                if src in ("elevator", "elevon", "pitch"):
                    cmd = self.pitch_cmd
                elif src in ("aileron", "roll"):
                    cmd = self.roll_cmd
                elif src in ("rudder", "yaw"):
                    cmd = self.yaw_cmd
            deg = cmd * surface.gain * surface.max_deg
            _set_axis(surface.node, surface.axis, surface.rest_hpr, deg)


def _set_axis(node: NodePath, axis: str, rest: tuple[float, float, float], delta: float) -> None:
    h, p, r = rest
    key = (axis or "Z").upper()
    if key == "X":
        node.setHpr(h, p, r + delta)
    elif key == "Y":
        node.setHpr(h, p + delta, r)
    else:
        node.setHpr(h + delta, p, r)


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


def _is_flight_clip(name: str, preferred: str) -> bool:
    if preferred and name == preferred:
        return True
    low = name.lower()
    if _is_presentational(low):
        return False
    if low.endswith("action") and not any(token in low for token in _FLIGHT_CLIP):
        return False
    return any(token in low for token in _FLIGHT_CLIP)


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
        if name not in order and _is_flight_clip(name, preferred):
            order.append(name)
    for name in order:
        ctrl = collection.find_anim(name)
        if ctrl:
            return ctrl, name
    return None, ""


def _find_node(root: NodePath, spec: str) -> NodePath:
    found = root.find(f"**/{spec}")
    if not found.isEmpty():
        return found
    return root.find(f"**/{spec}*")


def _rest(node: NodePath) -> tuple[float, float, float]:
    return float(node.getH()), float(node.getP()), float(node.getR())


def _skip_auto_node(name: str) -> bool:
    low = name.lower()
    if any(token in low for token in _SKIP_NODE):
        return True
    return low.endswith("_0")


def _covered(bound: list[BoundRotor], node: NodePath) -> bool:
    for item in bound:
        if item.node == node:
            return True
        try:
            if item.node.isAncestorOf(node) or node.isAncestorOf(item.node):
                return True
        except Exception:
            continue
    return False


def _bind_rotors(root: NodePath, nodes: list[NodePath], specs: list[RotorSpec]) -> list[BoundRotor]:
    bound: list[BoundRotor] = []
    if specs:
        for spec in specs:
            found = _find_node(root, spec.node)
            if found.isEmpty() or _covered(bound, found):
                continue
            bound.append(
                BoundRotor(found, spec.axis, float(spec.direction), rest_hpr=_rest(found))
            )
        return bound
    for node in nodes:
        name = node.getName()
        low = name.lower()
        if not any(h in low for h in _NAME_HINTS):
            continue
        if _skip_auto_node(name) or _covered(bound, node):
            continue
        bound.append(
            BoundRotor(node, "Z", 1.0 if len(bound) % 2 == 0 else -1.0, rest_hpr=_rest(node))
        )
    return bound


def _bind_surfaces(root: NodePath, specs: list[ControlSurfaceSpec]) -> list[BoundSurface]:
    out: list[BoundSurface] = []
    for spec in specs:
        found = _find_node(root, spec.node)
        if found.isEmpty():
            continue
        out.append(
            BoundSurface(
                found,
                spec.source,
                float(spec.gain),
                spec.axis,
                float(spec.max_deg or SURFACE_MAX),
                rest_hpr=_rest(found),
            )
        )
    return out


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

    specs = list(defn.animation.rotors) + list(defn.animation.propellers)
    rotors: list[BoundRotor] = []
    if clip is None:
        rotors = _bind_rotors(root, nodes, specs)
    surfaces = _bind_surfaces(root, defn.animation.control_surfaces)
    log.info("bound_rotors: %s", ", ".join(r.node.getName() for r in rotors) if rotors else "(none)")
    log.info("bound_surfaces: %s", ", ".join(s.node.getName() for s in surfaces) if surfaces else "(none)")

    animator = VisualAnimator(
        rotors=rotors,
        surfaces=surfaces,
        clips=clips,
        discovered=True,
        collection=collection,
        clip=clip,
        clip_name=clip_name,
        hangar=True,
    )
    animator.step(0.0)
    return animator
