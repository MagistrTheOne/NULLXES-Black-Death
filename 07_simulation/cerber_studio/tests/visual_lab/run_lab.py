"""Lighting V2 lab — offscreen Panda, no RenderPipeline. Product does not depend on this."""

from __future__ import annotations

from pathlib import Path

from panda3d.core import AmbientLight, DirectionalLight, Fog, Filename, PNMImage, Vec3
from direct.showbase.ShowBase import ShowBase

from studio.display import apply_panda_prc
from studio.config.settings import UserSettings
from studio.world import attach_wing
from studio.dynamics import preset
from studio.world_gen.geom import box, cone
from studio.world_gen.sky import apply_atmosphere, attach_haze, attach_sky
from studio.world_gen.weather import AtmosphereState


def run_lab(out: Path | None = None) -> Path:
    cfg = UserSettings()
    apply_panda_prc(cfg, width=960, height=540)
    base = ShowBase(windowType="offscreen")
    base.disableMouse()
    alight = AmbientLight("a")
    alnp = base.render.attachNewNode(alight)
    base.render.setLight(alnp)
    dlight = DirectionalLight("d")
    dlnp = base.render.attachNewNode(dlight)
    base.render.setLight(dlnp)
    sky = attach_sky(base.render)
    fog = attach_haze(base.render, 0.00008)
    atmos = AtmosphereState()
    atmos.apply_preset("sunset")
    sky = apply_atmosphere(base.render, sky, alight, dlight, fog, atmos, 0.00008)
    ground = base.render.attachNewNode(box((0.22, 0.30, 0.16)))
    ground.setScale(80, 80, 0.4)
    ground.setPos(0, 40, 0)
    for i in range(20):
        p = base.render.attachNewNode(cone((0.12, 0.22, 0.11)))
        p.setPos((i % 5) * 8 - 16, 20 + (i // 5) * 10, 2.2)
        p.setScale(1.6, 1.6, 3.4)
    wing = attach_wing(base.render, preset("ar_wing"))
    wing.setPos(0, 8, 1.4)
    wing.setHpr(20, 6, -8)
    lamp = base.render.attachNewNode(box((1.0, 0.9, 0.5)))
    lamp.setPos(4, 12, 0.4)
    lamp.setScale(0.2, 0.2, 0.3)
    lamp.setLightOff(1)
    base.camera.setPos(-14, -18, 8)
    base.camera.lookAt(0, 10, 1)
    base.graphicsEngine.renderFrame()
    base.graphicsEngine.renderFrame()
    target = out or Path.home() / ".nullxes" / "cerber_studio" / "visual_lab.png"
    target.parent.mkdir(parents=True, exist_ok=True)
    tex = base.win.getScreenshot()
    if tex:
        tex.write(Filename.fromOsSpecific(str(target)))
    ShowBase.destroy(base)
    return target


if __name__ == "__main__":
    path = run_lab()
    print(path)
