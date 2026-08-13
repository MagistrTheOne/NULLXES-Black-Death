"""Menu music pool: repo music/ + user drops. Random, no immediate repeat."""

from __future__ import annotations

import shutil
from pathlib import Path

from ..config.paths import MUSIC_DIR, STUDIO_ROOT, user_music_dir

AUDIO_EXTS = {".mp3", ".ogg", ".wav", ".flac", ".m4a"}
SLOT_COUNT = 8


def scan_playlist() -> list[Path]:
    found: dict[str, Path] = {}
    for folder in (MUSIC_DIR, STUDIO_ROOT / "assets" / "music", user_music_dir()):
        if not folder.is_dir():
            continue
        for path in sorted(folder.iterdir()):
            if path.is_file() and path.suffix.lower() in AUDIO_EXTS:
                found[path.name.lower()] = path
    return sorted(found.values(), key=lambda p: p.stem.lower())


def import_tracks(paths: list[Path]) -> list[Path]:
    dest = user_music_dir()
    imported: list[Path] = []
    for raw in paths:
        src = Path(raw)
        if not src.is_file() or src.suffix.lower() not in AUDIO_EXTS:
            continue
        target = dest / src.name
        if src.resolve() != target.resolve():
            shutil.copy2(src, target)
        imported.append(target)
    return imported
