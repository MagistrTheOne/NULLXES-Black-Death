"""Load GLB / procedural visuals. panda3d-gltf official path for .glb."""

from __future__ import annotations

import logging
import math
from pathlib import Path

from panda3d.core import NodePath, Vec3

from ..dynamics import PRESETS, WingParams, preset
from .animation import VisualAnimator, discover_and_bind
from .definition import AircraftClass, AircraftDefinition, VisualModel

log = logging.getLogger("cerber_studio.aircraft")

_GLTF_PATCHED = False
PREVIEW_SPAN = 3.2


def ensure_gltf(loader) -> bool:
    global _GLTF_PATCHED
    if _GLTF_PATCHED:
        return True
    try:
        import gltf

        if hasattr(gltf, "patch_loader"):
            gltf.patch_loader(loader)
            _GLTF_PATCHED = True
            return True
        if hasattr(gltf, "load_model"):
            _GLTF_PATCHED = True
            return True
    except Exception as exc:  # noqa: BLE001
        log.warning("gltf unavailable: %s", exc)
        return False
    return False


def to_wing_params(defn: AircraftDefinition) -> WingParams:
    key = defn.visual.procedural_key if defn.visual.procedural_key in PRESETS else None
    base = preset(key or "ar_wing")
    d = defn.demo_flight
    return WingParams(
        key=defn.id,
        title=defn.name,
        scale=defn.visual.scale if not defn.visual.auto_normalize else base.scale,
        max_speed=float(d.max_speed_mps),
        turn_rate_deg=float(d.turn_rate_deg),
        stall_speed=float(d.stall_speed_mps),
        cruise_speed=float(d.cruise_speed_mps),
        color_rgb=base.color_rgb,
        accent_rgb=base.accent_rgb,
    )


def visual_radius(node: NodePath) -> float:
    bounds = node.getTightBounds()
    if not bounds:
        return 1.6
    mn, mx = bounds
    size = mx - mn
    span = max(float(size.x), float(size.y), float(size.z), 1e-4)
    return span * 0.5


def frame_distance(radius: float, fov_deg: float, occupancy: float = 0.55, aspect: float = 16.0 / 9.0) -> float:
    vfov = math.radians(max(10.0, float(fov_deg)))
    hfov = 2.0 * math.atan(math.tan(vfov * 0.5) * aspect)
    return float(radius / max(1e-4, occupancy * math.tan(hfov * 0.5)))


def _apply_axes(node: NodePath, visual: VisualModel, class_: AircraftClass) -> None:
    up = (visual.up_axis or "Z").upper()
    if up == "Y":
        node.setP(-90.0)
    elif up == "X":
        node.setR(90.0)
    h, p, r = visual.rotation
    if h or p or r:
        node.setHpr(node.getH() + h, node.getP() + p, node.getR() + r)
    fwd = (visual.forward_axis or "Y").upper()
    if fwd == "X":
        node.setH(node.getH() + 90.0)
    elif fwd == "-Y":
        node.setH(node.getH() + 180.0)
    if class_ == AircraftClass.MULTIROTOR:
        node.setP(0.0)
        node.setR(0.0)


def _sit_and_scale(node: NodePath, visual: VisualModel) -> None:
    bounds = node.getTightBounds()
    if not bounds:
        node.setScale(visual.scale)
        return
    mn, mx = bounds
    size = mx - mn
    span = max(float(size.x), float(size.y), float(size.z), 1e-4)
    insane = span > 24.0 or span < 0.25
    normalize = visual.auto_normalize or insane
    scale = visual.scale * (PREVIEW_SPAN / span if normalize else 1.0)
    cx = (mn.x + mx.x) * 0.5
    cy = (mn.y + mx.y) * 0.5
    node.setPos(node, Vec3(-cx, -cy, -mn.z))
    node.setScale(scale)
    ox, oy, oz = visual.offset
    if ox or oy or oz:
        node.setPos(node.getX() + ox, node.getY() + oy, node.getZ() + oz)
    bounds = node.getTightBounds()
    if bounds:
        mn, _mx = bounds
        node.setZ(node.getZ() - mn.z)


def load_visual(loader, parent: NodePath, defn: AircraftDefinition) -> tuple[NodePath, str, VisualAnimator]:
    """Attach visual. Returns (preview_root, error, animator)."""
    from ..world import attach_wing

    visual = defn.visual
    preview = parent.attachNewNode(f"preview_{defn.id}")
    norm = preview.attachNewNode("aircraft_normalization_root")
    err = ""
    if visual.path is None or not visual.path.is_file():
        params = to_wing_params(defn)
        if visual.procedural_key in PRESETS:
            params = preset(visual.procedural_key)
            params = WingParams(
                key=defn.id,
                title=defn.name,
                scale=params.scale,
                max_speed=defn.demo_flight.max_speed_mps,
                turn_rate_deg=defn.demo_flight.turn_rate_deg,
                color_rgb=params.color_rgb,
                accent_rgb=params.accent_rgb,
            )
        model = attach_wing(norm, params)
        _sit_and_scale(model, visual)
        return preview, "", discover_and_bind(preview, defn)

    if not ensure_gltf(loader):
        attach_wing(norm, to_wing_params(defn))
        return preview, visual.path.name, VisualAnimator()

    try:
        model_np = None
        try:
            import gltf as gltf_mod

            if hasattr(gltf_mod, "load_model"):
                loaded = gltf_mod.load_model(str(visual.path))
                if loaded is not None:
                    model_np = NodePath(loaded) if not isinstance(loaded, NodePath) else loaded
        except Exception:  # noqa: BLE001
            model_np = None
        if model_np is None:
            model_np = loader.loadModel(str(visual.path))
        if model_np is None:
            raise RuntimeError("loader returned None")
        model_np.reparentTo(norm)
        _apply_axes(model_np, visual, defn.class_)
        _sit_and_scale(model_np, visual)
        try:
            preview.setShaderAuto()
        except Exception:
            pass
    except Exception as exc:  # noqa: BLE001
        log.exception("GLB load failed %s: %s", visual.path, exc)
        err = visual.path.name
        attach_wing(norm, to_wing_params(defn))
    return preview, err, discover_and_bind(preview, defn)
