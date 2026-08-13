"""Panda3D scene — glTF/GLB if present, else procedural flying-wing."""

from __future__ import annotations

from pathlib import Path

from panda3d.core import (
    Geom,
    GeomNode,
    GeomTriangles,
    GeomVertexData,
    GeomVertexFormat,
    GeomVertexWriter,
    NodePath,
    Vec4,
)

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets" / "airframes"


def _box(color: tuple[float, float, float]) -> GeomNode:
    fmt = GeomVertexFormat.getV3c4()
    vdata = GeomVertexData("box", fmt, Geom.UHStatic)
    vertex = GeomVertexWriter(vdata, "vertex")
    color_w = GeomVertexWriter(vdata, "color")
    corners = [
        (-1, -1, -1),
        (1, -1, -1),
        (1, 1, -1),
        (-1, 1, -1),
        (-1, -1, 1),
        (1, -1, 1),
        (1, 1, 1),
        (-1, 1, 1),
    ]
    c = Vec4(color[0], color[1], color[2], 1)
    for p in corners:
        vertex.addData3(*p)
        color_w.addData4(c)
    faces = (
        (0, 1, 2, 3),
        (4, 5, 6, 7),
        (0, 1, 5, 4),
        (2, 3, 7, 6),
        (0, 3, 7, 4),
        (1, 2, 6, 5),
    )
    tris = GeomTriangles(Geom.UHStatic)
    for a, b, c_i, d in faces:
        tris.addVertices(a, b, c_i)
        tris.addVertices(a, c_i, d)
    tris.closePrimitive()
    geom = Geom(vdata)
    geom.addPrimitive(tris)
    node = GeomNode("box")
    node.addGeom(geom)
    return node


def _wing_geom(color: tuple[float, float, float]) -> GeomNode:
    fmt = GeomVertexFormat.getV3c4()
    vdata = GeomVertexData("wing", fmt, Geom.UHStatic)
    vertex = GeomVertexWriter(vdata, "vertex")
    color_w = GeomVertexWriter(vdata, "color")
    verts = [
        (0.0, 1.2, 0.05),
        (-1.4, -0.9, 0.0),
        (1.4, -0.9, 0.0),
        (0.0, -0.2, 0.12),
        (0.0, -0.15, -0.08),
        (-0.25, -0.95, 0.02),
        (0.25, -0.95, 0.02),
    ]
    c = Vec4(color[0], color[1], color[2], 1)
    for v in verts:
        vertex.addData3(*v)
        color_w.addData4(c)
    tris = GeomTriangles(Geom.UHStatic)
    for a, b, c_i in (
        (0, 1, 3),
        (0, 3, 2),
        (0, 4, 1),
        (0, 2, 4),
        (1, 5, 3),
        (2, 3, 6),
        (1, 4, 5),
        (2, 6, 4),
        (3, 5, 6),
        (4, 6, 5),
    ):
        tris.addVertices(a, b, c_i)
    tris.closePrimitive()
    geom = Geom(vdata)
    geom.addPrimitive(tris)
    node = GeomNode("wing_mesh")
    node.addGeom(geom)
    return node


def attach_ground(parent: NodePath) -> None:
    ground = parent.attachNewNode(_box((0.16, 0.20, 0.14)))
    ground.setScale(400, 400, 0.04)
    ground.setPos(0, 0, 0)
    strip = parent.attachNewNode(_box((0.28, 0.28, 0.30)))
    strip.setScale(8, 80, 0.05)
    strip.setPos(0, 30, 0.05)


def _try_gltf(loader, filename: str, parent: NodePath, scale: float) -> NodePath | None:
    path = ASSETS / filename
    if not path.is_file():
        return None
    try:
        import gltf  # noqa: F401

        gltf.patch_loader(loader)
    except Exception:  # noqa: BLE001
        pass
    try:
        model = loader.loadModel(str(path))
        if model is None:
            return None
        root = parent.attachNewNode(path.stem)
        model.reparentTo(root)
        root.setScale(scale)
        return root
    except Exception:  # noqa: BLE001
        return None


def attach_ego(parent: NodePath, loader, *, glb_name: str, scale: float) -> NodePath:
    gltf_np = _try_gltf(loader, glb_name, parent, scale)
    if gltf_np is not None:
        return gltf_np
    root = parent.attachNewNode("ego_procedural")
    root.setScale(scale)
    mesh = root.attachNewNode(_wing_geom((0.08, 0.08, 0.09)))
    mesh.setTwoSided(True)
    accent = (0.70, 0.12, 0.16)
    for x in (-1.25, 1.25):
        tip = root.attachNewNode("tip")
        tip.setPos(x, -0.75, 0.02)
        tip.setScale(0.08, 0.18, 0.02)
        tip.attachNewNode(_box(accent))
    return root


def attach_target(parent: NodePath, loader, *, glb_name: str, scale: float) -> NodePath:
    gltf_np = _try_gltf(loader, glb_name, parent, scale * 0.7)
    if gltf_np is not None:
        return gltf_np
    t = parent.attachNewNode("target_uav")
    body = t.attachNewNode(_box((1.0, 0.55, 0.15)))
    body.setScale(0.45, 0.55, 0.12)
    wing = t.attachNewNode(_box((0.15, 0.15, 0.15)))
    wing.setScale(0.9, 0.18, 0.04)
    return t


def attach_extra(parent: NodePath, i: int) -> NodePath:
    n = parent.attachNewNode(f"bg_{i}")
    n.attachNewNode(_box((0.4, 0.42, 0.45)))
    n.setScale(0.35, 0.5, 0.08)
    return n
