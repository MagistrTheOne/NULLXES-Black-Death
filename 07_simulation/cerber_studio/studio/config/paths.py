"""Resolve BLACKBOX art and music from repo + studio assets."""

from pathlib import Path

STUDIO_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = STUDIO_ROOT.parents[1]
AIRFRAMES_DIR = STUDIO_ROOT / "assets" / "airframes"
MODELS_DIR = REPO_ROOT / "models"
MISSIONS_DIR = STUDIO_ROOT / "missions"
AUDIO_DIR = STUDIO_ROOT / "assets" / "audio"
UI_DIR = STUDIO_ROOT / "assets" / "ui"
BBOX_DIR = REPO_ROOT / "NULLXES_BBOX"
MUSIC_DIR = REPO_ROOT / "music"


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


def atmosphere_dir() -> Path:
    path = user_dir() / "atmosphere"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _first_file(*candidates: Path) -> Path | None:
    for path in candidates:
        if path.is_file():
            return path
    return None


def menu_background_path() -> Path | None:
    return _first_file(
        BBOX_DIR / "MENU.png",
        BBOX_DIR / "MENU.jpg",
        UI_DIR / "menu.png",
        UI_DIR / "menu.jpg",
    )


def menu_theme_path() -> Path | None:
    return _first_file(
        MUSIC_DIR / "Neon Highway.mp3",
        MUSIC_DIR / "Velvet Thunder.mp3",
        MUSIC_DIR / "menu-theme.mp3",
        AUDIO_DIR / "menu-theme.mp3",
    )


def user_music_dir() -> Path:
    path = user_dir() / "music"
    path.mkdir(parents=True, exist_ok=True)
    return path
