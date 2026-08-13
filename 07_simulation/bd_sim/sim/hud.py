"""HUD overlay — mode, energy, events. Not GSC voice."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QLabel


def make_hud(parent) -> QLabel:
    lab = QLabel(parent)
    lab.setAttribute(Qt.WA_TransparentForMouseEvents, True)
    lab.setAlignment(Qt.AlignLeft | Qt.AlignTop)
    lab.setFont(QFont("Consolas", 11))
    lab.setStyleSheet("color:#e8e8e8; background:rgba(0,0,0,140); padding:10px;")
    return lab


def format_hud(
    *,
    mode: str,
    tas: float,
    alt: float,
    thr: float,
    alpha: float,
    launched: bool,
    crashed: bool,
    stalled: bool,
    event: str,
    cerber: str,
    mission: str,
    dist: float,
) -> str:
    phase = "CRASH" if crashed else ("STALL" if stalled else ("AIR" if launched else "GND"))
    return (
        f"NULLXES BD-SIM  S1 arcade  NOT TWIN  NOT ARDUPLANE\n"
        f"MODE {mode:8s}  PHASE {phase:5s}  TAS {tas:5.1f} m/s  ALT {alt:6.1f} m\n"
        f"THR {thr:4.2f}  ALPHA {alpha:5.1f} deg  TGT {dist:6.1f} m\n"
        f"MSN {mission}\n"
        f"CERBER {cerber}\n"
        f"EVT {event or '-'}\n"
        f"WASD pitch/roll  Q yaw  E launch  Shift/Ctrl throttle  1-4 modes  R reset  F1 target"
    )
