"""User-data and studio roots. User settings live outside the git tree."""

from __future__ import annotations

from pathlib import Path

STUDIO_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = STUDIO_ROOT.parents[1]
AIRFRAMES_DIR = STUDIO_ROOT / "assets" / "airframes"
MODELS_DIR = REPO_ROOT / "models"
MISSIONS_DIR = STUDIO_ROOT / "missions"
AUDIO_DIR = STUDIO_ROOT / "assets" / "audio"


def user_dir() -> Path:
    path = Path.home() / ".nullxes" / "cerber_studio"
    path.mkdir(parents=True, exist_ok=True)
    return path


def settings_path() -> Path:
    return user_dir() / "settings.yaml"


def log_dir() -> Path:
    path = user_dir() / "logs"
    path.mkdir(parents=True, exist_ok=True)
    return path
