"""Aviation-style map. World truth. CERBER targets only if acquired."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter, QPen, QFont
from PySide6.QtWidgets import QWidget

from ..config.settings import UserSettings
from ..world_gen.graph import WorldGraph


class AviationMap(QWidget):
    def __init__(self, settings: UserSettings, parent=None) -> None:
        super().__init__(parent)
        self.settings = settings
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.graph: WorldGraph | None = None
        self.ego = (0.0, 0.0, 0.0)
        self.trail: list[tuple[float, float]] = []
        self.discovered: list[str] = []
        self.cerber_xy: tuple[float, float] | None = None
        self.scale_m = 18000.0

    def set_world(self, graph: WorldGraph, ego, trail, discovered, cerber_xy=None) -> None:
        self.graph = graph
        self.ego = ego
        self.trail = trail
        self.discovered = discovered
        self.cerber_xy = cerber_xy
        self.update()

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.fillRect(self.rect(), QColor(8, 9, 10, 210))
        if self.graph is None:
            return
        w, h = self.width(), self.height()
        cx, cy = w * 0.5, h * 0.55
        ex, ey = self.ego[0], self.ego[1]
        s = min(w, h) / (self.scale_m * 2.0)

        def xy(x, y):
            return cx + (x - ex) * s, cy - (y - ey) * s

        p.setPen(QPen(QColor(90, 100, 110), 1))
        for river in self.graph.rivers:
            for i in range(len(river) - 1):
                a, b = xy(*river[i]), xy(*river[i + 1])
                p.drawLine(int(a[0]), int(a[1]), int(b[0]), int(b[1]))
        p.setPen(QPen(QColor(160, 160, 150), 2))
        for road in self.graph.roads:
            for i in range(len(road) - 1):
                a, b = xy(*road[i]), xy(*road[i + 1])
                p.drawLine(int(a[0]), int(a[1]), int(b[0]), int(b[1]))
        font = QFont("Consolas", 9)
        p.setFont(font)
        p.setPen(QColor(200, 200, 196))
        for lm in self.graph.landmarks:
            title = str(lm.extra.get("title") or lm.kind.upper())
            if lm.extra.get("discover") and title not in self.discovered and lm.kind != "airfield":
                continue
            px, py = xy(lm.x, lm.y)
            p.drawText(int(px) + 6, int(py) - 4, title)
            p.drawEllipse(int(px) - 3, int(py) - 3, 6, 6)
        p.setPen(QPen(QColor(240, 240, 240), 2))
        if len(self.trail) > 1:
            for i in range(max(0, len(self.trail) - 80), len(self.trail) - 1):
                a, b = xy(*self.trail[i][:2]), xy(*self.trail[i + 1][:2])
                p.drawLine(int(a[0]), int(a[1]), int(b[0]), int(b[1]))
        ox, oy = xy(ex, ey)
        p.setBrush(QColor(240, 240, 240))
        p.drawEllipse(int(ox) - 4, int(oy) - 4, 8, 8)
        p.drawText(int(ox) + 8, int(oy) + 4, "YOU")
        if self.cerber_xy is not None:
            tx, ty = xy(*self.cerber_xy)
            p.setPen(QColor(180, 180, 180))
            p.drawText(int(tx), int(ty), "TRK")
        p.setPen(QColor(160, 160, 160))
        p.drawText(24, 32, "N")
        p.drawText(24, 52, f"SEED  {self.graph.seed}")
        p.drawText(24, h - 24, "MAP   world truth")
