"""Procedural hangar atmosphere — rain loop + thunder. Cached WAV, no sample pack required."""

from __future__ import annotations

import math
import wave
from pathlib import Path

import numpy as np

from ..config.paths import atmosphere_dir

RATE = 44100


def _write_wav(path: Path, samples: np.ndarray) -> None:
    pcm = np.clip(samples, -0.99, 0.99)
    stereo = np.column_stack((pcm, pcm)) if pcm.ndim == 1 else pcm
    data = (stereo * 32767.0).astype(np.int16)
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(RATE)
        wf.writeframes(data.tobytes())


def rain_path() -> Path:
    path = atmosphere_dir() / "rain_loop.wav"
    if path.is_file() and path.stat().st_size > 1000:
        return path
    rng = np.random.default_rng(7)
    n = RATE * 8
    noise = rng.standard_normal(n).astype(np.float64)
    kernel = np.exp(-np.linspace(0, 8, 96))
    kernel /= kernel.sum()
    wet = np.convolve(noise, kernel, mode="same")
    high = wet - np.convolve(wet, np.ones(12) / 12.0, mode="same")
    drops = rng.random(n)
    ticks = (drops > 0.992).astype(np.float64) * rng.uniform(0.15, 0.45, n)
    sig = 0.22 * high + 0.08 * ticks
    fade = np.linspace(0, 1, 2048)
    sig[:2048] *= fade
    sig[-2048:] *= fade[::-1]
    _write_wav(path, sig * 0.55)
    return path


def thunder_path(variant: int = 0) -> Path:
    path = atmosphere_dir() / f"thunder_{variant}.wav"
    if path.is_file() and path.stat().st_size > 1000:
        return path
    rng = np.random.default_rng(11 + variant)
    n = int(RATE * (2.4 + variant * 0.5))
    t = np.arange(n) / RATE
    rumble = np.sin(2 * math.pi * (38 + variant * 6) * t) * np.exp(-t * 1.15)
    rumble += 0.45 * np.sin(2 * math.pi * (22 + variant * 3) * t) * np.exp(-t * 0.7)
    crack = rng.standard_normal(n) * np.exp(-t * (3.5 + variant))
    onset = int(0.08 * RATE)
    env = np.ones(n)
    env[:onset] = np.linspace(0, 1, onset)
    sig = (0.55 * rumble + 0.35 * crack) * env
    _write_wav(path, sig * 0.85)
    return path


def engine_loop_path() -> Path:
    path = atmosphere_dir() / "engine_loop.wav"
    if path.is_file() and path.stat().st_size > 1000:
        return path
    n = RATE * 2
    t = np.arange(n) / RATE
    blade = 0.22 * np.sin(2 * math.pi * 78 * t)
    blade += 0.12 * np.sin(2 * math.pi * 156 * t)
    motor = 0.08 * np.sin(2 * math.pi * 41 * t)
    rng = np.random.default_rng(3)
    hiss = 0.03 * rng.standard_normal(n)
    sig = blade + motor + hiss
    fade = np.linspace(0, 1, 512)
    sig[:512] *= fade
    sig[-512:] *= fade[::-1]
    _write_wav(path, sig * 0.7)
    return path


def wind_loop_path() -> Path:
    path = atmosphere_dir() / "wind_loop.wav"
    if path.is_file() and path.stat().st_size > 1000:
        return path
    rng = np.random.default_rng(19)
    n = RATE * 4
    noise = rng.standard_normal(n)
    kernel = np.exp(-np.linspace(0, 6, 64))
    kernel /= kernel.sum()
    whoosh = np.convolve(noise, kernel, mode="same")
    t = np.arange(n) / RATE
    sig = 0.35 * whoosh + 0.08 * np.sin(2 * math.pi * 9.0 * t) * whoosh
    fade = np.linspace(0, 1, 1024)
    sig[:1024] *= fade
    sig[-1024:] *= fade[::-1]
    _write_wav(path, sig * 0.5)
    return path


def ensure_atmosphere() -> tuple[Path, list[Path]]:
    rain = rain_path()
    bolts = [thunder_path(i) for i in range(3)]
    engine_loop_path()
    wind_loop_path()
    return rain, bolts
