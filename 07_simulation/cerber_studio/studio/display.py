"""Display geometry and Panda3D boot PRC. No OS display-mode switching."""

from __future__ import annotations

from panda3d.core import loadPrcFileData
from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QGuiApplication, QScreen
from PySide6.QtWidgets import QWidget

from .config.settings import RESOLUTION_CANDIDATES, UserSettings

_PRC_DONE = False


def primary_screen() -> QScreen:
    app = QGuiApplication.instance()
    screen = app.primaryScreen() if app is not None else None
    if screen is None:
        raise RuntimeError("No display")
    return screen


def screen_size(screen: QScreen | None = None) -> tuple[int, int]:
    sc = screen or primary_screen()
    g = sc.geometry()
    return int(g.width()), int(g.height())


def supported_resolutions(screen: QScreen | None = None) -> list[tuple[int, int]]:
    sw, sh = screen_size(screen)
    out = [(w, h) for w, h in RESOLUTION_CANDIDATES if w <= sw and h <= sh]
    native = (sw, sh)
    if native not in out:
        out.append(native)
    if not out:
        out = [native]
    return out


def clamp_resolution(requested: list[int] | tuple[int, int], screen: QScreen | None = None) -> tuple[int, int]:
    sw, sh = screen_size(screen)
    rw = int(requested[0]) if requested else 1920
    rh = int(requested[1]) if requested and len(requested) > 1 else 1080
    modes = supported_resolutions(screen)
    if (rw, rh) in modes:
        return rw, rh
    fit = [(w, h) for w, h in modes if w <= sw and h <= sh]
    if not fit:
        return sw, sh
    fit.sort(key=lambda p: abs(p[0] * p[1] - rw * rh))
    return fit[0]


def apply_window_display(win: QWidget, settings: UserSettings) -> tuple[int, int]:
    screen = win.screen() or primary_screen()
    geom: QRect = screen.geometry()
    sw, sh = geom.width(), geom.height()
    rw, rh = clamp_resolution(settings.display.resolution, screen)
    settings.display.resolution = [rw, rh]
    mode = settings.display.mode
    win.setWindowFlag(Qt.FramelessWindowHint, mode == "borderless")
    if mode == "fullscreen":
        win.setGeometry(geom)
        win.showFullScreen()
        return sw, sh
    win.setWindowState(win.windowState() & ~Qt.WindowFullScreen)
    if mode == "borderless":
        win.setGeometry(geom)
        win.show()
        return sw, sh
    x = geom.x() + max(0, (sw - rw) // 2)
    y = geom.y() + max(0, (sh - rh) // 2)
    win.setGeometry(x, y, min(rw, sw), min(rh, sh))
    win.showNormal()
    return min(rw, sw), min(rh, sh)


def framebuffer_size(window_w: int, window_h: int, settings: UserSettings) -> tuple[int, int]:
    rw, rh = clamp_resolution(settings.display.resolution)
    scale = float(max(0.5, min(1.5, settings.graphics.render_scale)))
    w = max(640, int(min(window_w, rw) * scale))
    h = max(360, int(min(window_h, rh) * scale))
    return w, h


def view_distance_far(quality: str) -> float:
    return {"low": 800.0, "medium": 1400.0, "high": 2500.0}.get(quality, 2000.0)


def apply_panda_prc(settings: UserSettings, *, width: int, height: int) -> None:
    global _PRC_DONE
    if _PRC_DONE:
        return
    loadPrcFileData("", "window-type offscreen")
    loadPrcFileData("", "audio-library-name null")
    loadPrcFileData("", "framebuffer-hardware true")
    loadPrcFileData("", "sync-video false")
    loadPrcFileData("", "show-frame-rate-meter 0")
    loadPrcFileData("", "notify-level-util error")
    loadPrcFileData("", "notify-level-glgsg error")
    loadPrcFileData("", f"win-size {int(width)} {int(height)}")
    msaa = int(settings.graphics.msaa)
    if msaa >= 2:
        loadPrcFileData("", "framebuffer-multisample 1")
        loadPrcFileData("", f"multisamples {int(msaa)}")
    _PRC_DONE = True


def timer_interval_ms(settings: UserSettings, refresh_hz: float) -> int:
    limit = int(settings.display.fps_limit)
    cap = refresh_hz if settings.display.vsync else 1000.0
    if limit > 0:
        cap = min(cap, float(limit)) if settings.display.vsync else float(limit)
    if cap <= 0:
        return 1
    return max(1, int(round(1000.0 / cap)))


def apply_texture_quality(quality: str) -> None:
    from panda3d.core import SamplerState, Texture

    q = (quality or "high").lower()
    if q == "low":
        Texture.setDefaultMinfilter(SamplerState.FTLinear)
        Texture.setDefaultMagfilter(SamplerState.FTLinear)
        Texture.setDefaultAnisotropicDegree(1)
    elif q == "medium":
        Texture.setDefaultMinfilter(SamplerState.FTLinearMipmapLinear)
        Texture.setDefaultMagfilter(SamplerState.FTLinear)
        Texture.setDefaultAnisotropicDegree(4)
    else:
        Texture.setDefaultMinfilter(SamplerState.FTLinearMipmapLinear)
        Texture.setDefaultMagfilter(SamplerState.FTLinear)
        Texture.setDefaultAnisotropicDegree(8)
