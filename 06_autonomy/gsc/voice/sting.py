"""NULLXES-owned DEFENSE sting. Procedural. No third-party track."""

from __future__ import annotations

import math
import struct
import tempfile
import wave
from pathlib import Path

SAMPLE_RATE = 22050
DURATION_S = 2.15


def render_defense_sting() -> bytes:
    n = int(SAMPLE_RATE * DURATION_S)
    frames = bytearray()
    for i in range(n):
        t = i / SAMPLE_RATE
        env = 0.0
        if t < 0.08:
            env = t / 0.08
        elif t < 0.45:
            env = 1.0
        else:
            env = max(0.0, 1.0 - (t - 0.45) / 1.7)
        hit = math.sin(2.0 * math.pi * 55.0 * t) * 0.55
        drop_f = 180.0 * (1.0 - 0.72 * min(1.0, t / 1.6))
        drop = math.sin(2.0 * math.pi * drop_f * t) * 0.35
        grit = 0.12 * math.sin(2.0 * math.pi * 1111.0 * t + 4.0 * math.sin(40.0 * t))
        if 0.12 <= t <= 0.22:
            hit += 0.4 * math.sin(2.0 * math.pi * 38.0 * t)
        sample = max(-0.95, min(0.95, env * (hit + drop + grit)))
        frames += struct.pack("<h", int(sample * 32767.0))
    return bytes(frames)


def write_defense_sting(path: Path | None = None) -> Path:
    out = path or Path(tempfile.gettempdir()) / "nullxes_defense_sting.wav"
    pcm = render_defense_sting()
    with wave.open(str(out), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(pcm)
    return out
