"""Resolve CERBER V2 pack + repo roots."""
from __future__ import annotations

from pathlib import Path

PACK = Path(__file__).resolve().parents[1]
REPO = Path(__file__).resolve().parents[4]
CONFIGS = PACK / "configs"
SCRIPTS = PACK / "scripts"
