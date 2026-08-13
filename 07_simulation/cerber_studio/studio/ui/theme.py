"""NULLXES × dark industrial. No neon, no glow, no sci-fi chrome."""

from __future__ import annotations

from PySide6.QtWidgets import QWidget

from ..config.settings import UserSettings

REF_W = 1920.0
REF_H = 1080.0

COLORS = {
    "bg": "#0B0B0C",
    "panel": "rgba(16,16,18,210)",
    "stroke": "rgba(255,255,255,28)",
    "text": "#EDEDED",
    "muted": "#8A8A8E",
    "accent": "#C8C8C8",
}


def ui_factor(widget: QWidget, settings: UserSettings) -> float:
    w = max(1, widget.width())
    h = max(1, widget.height())
    base = min(w / REF_W, h / REF_H)
    pref = (settings.display.ui_scale or "auto").lower()
    if pref == "auto":
        return max(0.65, min(2.2, base))
    try:
        pct = float(pref) / 100.0
    except ValueError:
        pct = 1.0
    return max(0.65, min(2.4, base * pct))


def scale_px(widget: QWidget, settings: UserSettings, value: int) -> int:
    return max(1, int(round(value * ui_factor(widget, settings))))


STYLESHEET = """
QWidget#ProductRoot {
  background: #000000;
  color: #EDEDED;
  font-family: "Segoe UI", "Helvetica Neue", Arial;
}
QWidget#GlassPanel {
  background: rgba(12,12,14,188);
  border: 1px solid rgba(255,255,255,26);
}
QLabel#Brand {
  color: #F4F4F4;
  font-weight: 600;
  letter-spacing: 4px;
  background: transparent;
}
QLabel#Muted {
  color: #8A8A8E;
  background: transparent;
}
QLabel#Title {
  color: #F2F2F2;
  font-weight: 500;
  background: transparent;
}
QPushButton#MenuBtn {
  background: rgba(18,18,20,160);
  border: 1px solid rgba(255,255,255,22);
  color: #F0F0F0;
  text-align: center;
  padding: 14px 22px;
}
QPushButton#MenuBtn:hover {
  background: rgba(32,32,34,200);
  border: 1px solid rgba(255,255,255,40);
}
QPushButton#MenuBtn:pressed {
  background: rgba(8,8,9,220);
}
QPushButton#PrimaryBtn {
  background: #F2F2F2;
  color: #111113;
  border: none;
  font-weight: 600;
  padding: 12px 28px;
}
QPushButton#PrimaryBtn:hover { background: #FFFFFF; }
QPushButton#PrimaryBtn:pressed { background: #D8D8D8; }
QPushButton#GhostBtn {
  background: transparent;
  color: #D0D0D0;
  border: 1px solid rgba(255,255,255,30);
  padding: 10px 18px;
}
QPushButton#GhostBtn:hover { background: rgba(255,255,255,14); }
QComboBox, QSpinBox, QDoubleSpinBox, QSlider, QCheckBox, QLineEdit {
  color: #EDEDED;
  background: rgba(20,20,22,200);
  border: 1px solid rgba(255,255,255,22);
  padding: 4px 8px;
}
QComboBox QAbstractItemView {
  background: #141416;
  color: #EDEDED;
  selection-background-color: #2A2A2E;
}
QListWidget {
  background: transparent;
  border: none;
  color: #EDEDED;
  outline: none;
}
QListWidget::item { padding: 10px 8px; }
QListWidget::item:selected { background: rgba(255,255,255,16); }
QSlider::groove:horizontal { height: 2px; background: rgba(255,255,255,40); }
QSlider::handle:horizontal {
  width: 12px; height: 12px; margin: -6px 0;
  background: #F0F0F0; border-radius: 6px;
}
QScrollArea { border: none; background: transparent; }
"""
