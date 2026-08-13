"""Single pygame mixer backend. Music is independent of render/physics."""

from __future__ import annotations

import logging
import random

from pathlib import Path

import yaml

from ..config.paths import STUDIO_ROOT, menu_theme_path
from ..config.settings import AudioSettings
from .atmosphere import engine_loop_path, ensure_atmosphere, wind_loop_path
from .playlist import scan_playlist

log = logging.getLogger("cerber_studio.audio")

try:
    from PySide6.QtCore import QTimer

    _QT = True
except Exception:  # noqa: BLE001
    _QT = False

try:
    import pygame

    _PYGAME = True
except Exception:  # noqa: BLE001
    _PYGAME = False

CH_RAIN = 0
CH_THUNDER = 1
CH_ENGINE = 4
CH_WIND = 5


def _load_mix() -> dict:
    path = STUDIO_ROOT / "assets" / "audio" / "flight_mix.yaml"
    if not path.is_file():
        return {}
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception:
        return {}


class MusicDirector:
    def __init__(self) -> None:
        self.tracks: list = []
        self.index = -1
        self.shuffle = True
        self._last = None
        self.now_playing = ""
        self.mix = _load_mix()

    def scan(self) -> None:
        self.tracks = scan_playlist()
        self.mix = _load_mix()

    def _by_stem(self, name: str):
        key = name.lower()
        for p in self.tracks:
            if p.stem.lower() == key or p.name.lower() == key:
                return p
        return None

    def pick_mix(self, ctx: dict):
        rules = (self.mix or {}).get("tracks") or {}
        scored: list = []
        for stem, tags in rules.items():
            path = self._by_stem(str(stem))
            if path is None:
                continue
            score = 0
            for field, val in (
                ("regions", ctx.get("region")),
                ("tod", ctx.get("tod")),
                ("weather", ctx.get("weather")),
                ("intensity", ctx.get("intensity")),
                ("mission", ctx.get("mission")),
            ):
                pack = [str(x).lower() for x in (tags.get(field) or [])]
                if val and pack and str(val).lower() in pack:
                    score += 1
            if score:
                scored.append((score, path))
        if scored:
            scored.sort(key=lambda x: -x[0])
            top = scored[0][0]
            pool = [p for s, p in scored if s == top and p != self._last] or [p for s, p in scored if s == top]
            return random.choice(pool)
        return None

    def _pick(self, delta: int = 1) -> object | None:
        if not self.tracks:
            self.scan()
        if not self.tracks:
            return menu_theme_path()
        if self.shuffle:
            pool = [p for p in self.tracks if p != self._last]
            if not pool:
                pool = list(self.tracks)
            return random.choice(pool)
        if self.index < 0:
            self.index = 0
        else:
            self.index = (self.index + delta) % len(self.tracks)
        return self.tracks[self.index]

    def load_and_play(self, path, volume: float) -> bool:
        if not _PYGAME or path is None:
            return False
        try:
            pygame.mixer.music.load(str(path))
            pygame.mixer.music.set_volume(volume)
            pygame.mixer.music.play(0)
            self._last = path
            self.now_playing = path.stem
            if path in self.tracks:
                self.index = self.tracks.index(path)
            return True
        except Exception as exc:  # noqa: BLE001
            log.warning("music load failed %s: %s", path, exc)
            return False

    def play_index(self, index: int, volume: float) -> None:
        if not self.tracks or index < 0 or index >= len(self.tracks):
            return
        self.load_and_play(self.tracks[index], volume)

    def play(self, volume: float, ctx: dict | None = None) -> None:
        pick = self.pick_mix(ctx or {}) if ctx else None
        if pick is None:
            pick = self._pick(1)
        self.load_and_play(pick, volume)

    def next(self, volume: float) -> None:
        if self.shuffle:
            self.play(volume)
            return
        pick = self._pick(1)
        self.load_and_play(pick, volume)

    def previous(self, volume: float) -> None:
        pick = self._pick(-1)
        self.load_and_play(pick, volume)

    def pause(self) -> None:
        if _PYGAME:
            pygame.mixer.music.pause()

    def resume(self) -> None:
        if _PYGAME:
            pygame.mixer.music.unpause()


class AudioManager:
    def __init__(self) -> None:
        self.throttle = 0.0
        self.airspeed = 0.0
        self.max_speed = 34.0
        self.scene = "menu"
        self._settings = AudioSettings()
        self._mixer = False
        self._rain = None
        self._thunder: list = []
        self._engine = None
        self._wind = None
        self._thunder_timer = None
        self._music_poll = None
        self._vol_timer = None
        self.music = MusicDirector()
        self._eng_vol = 0.0
        self._wind_vol = 0.0
        self._music_mul = 1.0
        self.mix_ctx: dict = {}
        self.camera_mode = "chase"
        self._pan = 0.0
        self._music_paused = False
        self.rain_level = 0.0
        self.storm_level = 0.0

    def current_track_name(self) -> str:
        return self.music.now_playing

    def reload_playlist(self) -> None:
        self.music.scan()
        if self._mixer and not self._settings.muted and not self._music_busy():
            self.music.play(self._music_vol())

    def play_slot(self, index: int) -> None:
        if self._settings.muted:
            return
        self._ensure_mixer()
        self.music.play_index(index, self._music_vol())

    def apply(self, settings: AudioSettings) -> None:
        self._settings = settings
        if settings.muted:
            self.stop()
            return
        self._ensure_mixer()
        self._apply_volumes()
        if self.scene in ("menu", "hangar", "loading") and not self._music_busy():
            self._ensure_menu_layers()
        if self.scene in ("flight", "paused") and self._engine is not None:
            self._ensure_flight_layers()

    def set_scene(self, scene: str) -> None:
        prev = self.scene
        self.scene = scene
        if self._settings.muted:
            self.stop()
            return
        self._ensure_mixer()
        if scene in ("menu", "hangar"):
            self._music_mul = 1.0
            self._ensure_menu_layers()
            self._stop_flight_layers()
        elif scene == "loading":
            self._music_mul = 0.45
            self._ensure_menu_layers()
            self._stop_flight_layers()
        elif scene == "paused":
            self._music_mul = 0.7
            self._ensure_music()
            self._ensure_flight_layers()
            self._stop_storm()
        else:
            self._music_mul = 0.62
            self._ensure_music()
            self._ensure_flight_layers()
            self._stop_storm()
        if prev != scene:
            self._apply_volumes()

    def stop(self) -> None:
        self._stop_storm()
        self._stop_flight_layers()
        if self._music_poll is not None:
            self._music_poll.stop()
            self._music_poll = None
        if self._vol_timer is not None:
            self._vol_timer.stop()
            self._vol_timer = None
        self.music.now_playing = ""
        if not self._mixer:
            return
        try:
            pygame.mixer.music.stop()
            pygame.mixer.stop()
        except Exception:  # noqa: BLE001
            pass

    def _ensure_mixer(self) -> None:
        if self._mixer or not _PYGAME:
            return
        try:
            pygame.mixer.pre_init(44100, -16, 2, 8192)
            pygame.mixer.init()
            pygame.mixer.set_num_channels(16)
            rain_path, bolts = ensure_atmosphere()
            self._rain = pygame.mixer.Sound(str(rain_path))
            self._thunder = [pygame.mixer.Sound(str(p)) for p in bolts]
            self._engine = pygame.mixer.Sound(str(engine_loop_path()))
            self._wind = pygame.mixer.Sound(str(wind_loop_path()))
            self._mixer = True
            self.music.scan()
            if _QT:
                self._vol_timer = QTimer()
                self._vol_timer.timeout.connect(self._smooth_buses)
                self._vol_timer.start(50)
                self._music_poll = QTimer()
                self._music_poll.timeout.connect(self._poll_music)
                self._music_poll.start(400)
        except Exception as exc:  # noqa: BLE001
            log.warning("mixer init failed: %s", exc)
            self._mixer = False

    def _music_busy(self) -> bool:
        if not self._mixer:
            return False
        try:
            return bool(pygame.mixer.music.get_busy())
        except Exception:  # noqa: BLE001
            return False

    def _music_vol(self) -> float:
        a = self._settings
        return float(max(0.0, min(1.0, a.master * a.music * self._music_mul)))

    def _bus(self, channel: float) -> float:
        a = self._settings
        return float(max(0.0, min(1.0, a.master * channel)))

    def _ensure_music(self) -> None:
        if not self._mixer or self._settings.muted:
            return
        if self._music_busy():
            pygame.mixer.music.set_volume(self._music_vol())
            pygame.mixer.music.unpause()
            return
        ctx = self.mix_ctx if self.scene in ("flight", "paused") else {}
        self.music.play(self._music_vol(), ctx or None)

    def _ensure_menu_layers(self) -> None:
        self._ensure_music()
        if self._rain is not None and not pygame.mixer.Channel(CH_RAIN).get_busy():
            pygame.mixer.Channel(CH_RAIN).play(self._rain, loops=-1)
        if self._thunder_timer is None and _QT:
            self._thunder_timer = QTimer()
            self._thunder_timer.timeout.connect(self._strike)
            self._arm_thunder()

    def _ensure_flight_layers(self) -> None:
        if not self._mixer:
            return
        if self._engine is not None and not pygame.mixer.Channel(CH_ENGINE).get_busy():
            pygame.mixer.Channel(CH_ENGINE).play(self._engine, loops=-1)
        if self._wind is not None and not pygame.mixer.Channel(CH_WIND).get_busy():
            pygame.mixer.Channel(CH_WIND).play(self._wind, loops=-1)

    def _stop_flight_layers(self) -> None:
        if not self._mixer:
            return
        pygame.mixer.Channel(CH_ENGINE).stop()
        pygame.mixer.Channel(CH_WIND).stop()
        self._eng_vol = 0.0
        self._wind_vol = 0.0

    def _stop_storm(self) -> None:
        if self._thunder_timer is not None:
            self._thunder_timer.stop()
            self._thunder_timer = None
        if not self._mixer:
            return
        pygame.mixer.Channel(CH_RAIN).stop()
        pygame.mixer.Channel(CH_THUNDER).stop()

    def _arm_thunder(self) -> None:
        if self._thunder_timer is None:
            return
        self._thunder_timer.start(int(random.uniform(8000, 18000)))

    def _strike(self) -> None:
        if not self._mixer or self.scene not in ("menu", "hangar", "loading") or not self._thunder:
            self._arm_thunder()
            return
        pygame.mixer.Channel(CH_THUNDER).play(random.choice(self._thunder))
        pygame.mixer.Channel(CH_THUNDER).set_volume(self._bus(self._settings.environment) * random.uniform(0.5, 1.0))
        self._arm_thunder()

    def _poll_music(self) -> None:
        if not self._mixer or self._settings.muted:
            return
        if not self._music_busy():
            ctx = self.mix_ctx if self.scene in ("flight", "paused") else {}
            self.music.play(self._music_vol(), ctx or None)

    def _apply_volumes(self) -> None:
        if not self._mixer:
            return
        pygame.mixer.music.set_volume(self._music_vol())
        rain = self._bus(self._settings.environment) * (0.5 if self.scene in ("menu", "hangar") else self.rain_level)
        pygame.mixer.Channel(CH_RAIN).set_volume(rain)
        self._smooth_buses()

    def toggle_music(self) -> None:
        if not self._mixer:
            return
        if self._music_paused:
            pygame.mixer.music.unpause()
            self._music_paused = False
        else:
            pygame.mixer.music.pause()
            self._music_paused = True

    def seek_frac(self, frac: float) -> None:
        if not self._mixer:
            return
        try:
            pygame.mixer.music.set_pos(max(0.0, frac) * 180.0)
        except Exception:
            pass

    def music_frac(self) -> float:
        if not self._mixer:
            return 0.0
        try:
            ms = pygame.mixer.music.get_pos()
            return float(max(0.0, min(1.0, (ms / 1000.0) / 180.0))) if ms >= 0 else 0.0
        except Exception:
            return 0.0

    def next_track(self) -> None:
        self.music.next(self._music_vol())

    def prev_track(self) -> None:
        self.music.previous(self._music_vol())

    def toggle_shuffle(self) -> None:
        self.music.shuffle = not self.music.shuffle

    def _smooth_buses(self) -> None:
        if not self._mixer or self._settings.muted:
            return
        flying = self.scene in ("flight", "paused")
        thr = max(0.0, min(1.0, self.throttle))
        spd = max(0.0, min(1.0, self.airspeed / max(8.0, self.max_speed)))
        cam = self.camera_mode
        eng_mul = 1.0 if cam in ("chase", "orbit", "ground") else 0.42 if cam == "nose" else 0.7
        wind_mul = 1.0 if cam == "nose" else 0.55 if cam in ("chase", "orbit") else 0.8
        eng_t = (0.08 + 0.92 * thr) * self._bus(self._settings.engine) * eng_mul if flying else 0.0
        wind_t = (spd * spd * 0.85 + spd * 0.15) * self._bus(self._settings.wind) * wind_mul if flying else 0.0
        self._eng_vol += (eng_t - self._eng_vol) * 0.18
        self._wind_vol += (wind_t - self._wind_vol) * 0.12
        pan = 0.0
        if cam == "flyby":
            pan = max(-0.85, min(0.85, self._pan))
        left = max(0.0, 1.0 - pan)
        right = max(0.0, 1.0 + pan)
        try:
            pygame.mixer.Channel(CH_ENGINE).set_volume(self._eng_vol * left, self._eng_vol * right)
            pygame.mixer.Channel(CH_WIND).set_volume(self._wind_vol * left, self._wind_vol * right)
        except TypeError:
            pygame.mixer.Channel(CH_ENGINE).set_volume(max(0.0, self._eng_vol))
            pygame.mixer.Channel(CH_WIND).set_volume(max(0.0, self._wind_vol))
        pygame.mixer.music.set_volume(self._music_vol())
        if flying and self.rain_level > 0.05:
            if self._rain is not None and not pygame.mixer.Channel(CH_RAIN).get_busy():
                pygame.mixer.Channel(CH_RAIN).play(self._rain, loops=-1)
            pygame.mixer.Channel(CH_RAIN).set_volume(self._bus(self._settings.environment) * self.rain_level)
        if flying and self.storm_level > 0.4 and self._thunder:
            if random.random() < 0.008:
                pygame.mixer.Channel(CH_THUNDER).play(random.choice(self._thunder))
                pygame.mixer.Channel(CH_THUNDER).set_volume(self._bus(self._settings.environment) * self.storm_level)
