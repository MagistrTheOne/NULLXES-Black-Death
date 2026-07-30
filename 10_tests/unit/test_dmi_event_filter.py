"""Event filter tests."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "06_autonomy"))

from dmi.event_bus import EventFilter, fingerprint_mode


def test_dedupe():
    f = EventFilter()
    assert f.should_publish("mode", fingerprint_mode("NOMINAL")) is True
    assert f.should_publish("mode", fingerprint_mode("NOMINAL")) is False
    assert f.should_publish("mode", fingerprint_mode("RTB")) is True
