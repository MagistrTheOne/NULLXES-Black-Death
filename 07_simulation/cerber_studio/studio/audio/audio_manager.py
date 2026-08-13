"""Electric fixed-wing audio. Mute stops the device; no quadcopter samples."""

from __future__ import annotations

import math
import struct

from ..config.settings import AudioSettings

try:
    from PySide6.QtCore import QTimer
    from PySide6.QtMultimedia import QAudioFormat, QAudioSink, QMediaDevices

    _AUDIO_OK = True
except Exception:  # noqa: BLE001
    _AUDIO_OK = False


class AudioManager:
    def __init__(self) -> None:
        self._sink = None
        self._io = None
        self._timer: QTimer | None = None
        self._phase_prop = 0.0
        self._phase_mot = 0.0
        self._rate = 22050
        self._enabled = False
        self.throttle = 0.55
        self.airspeed = 14.0
        self.max_speed = 34.0
        self.scene = "hangar"
        self._settings = AudioSettings()

    def apply(self, settings: AudioSettings) -> None:
        self._settings = settings
        if settings.muted or not _AUDIO_OK:
            self.stop()
            return
        self.start()

    def start(self) -> None:
        if not _AUDIO_OK or self._settings.muted:
            self.stop()
            return
        if self._sink is not None:
            return
        fmt = QAudioFormat()
        fmt.setSampleRate(self._rate)
        fmt.setChannelCount(1)
        fmt.setSampleFormat(QAudioFormat.Int16)
        device = QMediaDevices.defaultAudioOutput()
        if device is None:
            return
        self._sink = QAudioSink(device, fmt)
        self._io = self._sink.start()
        self._timer = QTimer()
        self._timer.timeout.connect(self._pump)
        self._timer.start(40)
        self._enabled = True

    def stop(self) -> None:
        self._enabled = False
        if self._timer is not None:
            self._timer.stop()
            self._timer = None
        if self._sink is not None:
            self._sink.stop()
            self._sink = None
            self._io = None

    def _pump(self) -> None:
        if self._io is None or not self._enabled:
            return
        n = int(self._rate * 0.04)
        a = self._settings
        master = a.master
        thr = max(0.05, min(1.0, self.throttle))
        spd = max(0.0, min(1.0, self.airspeed / max(8.0, self.max_speed)))
        buf = bytearray()
        for i in range(n):
            t = 1.0 / self._rate
            rpm = 70.0 + thr * 90.0
            self._phase_prop += 2.0 * math.pi * rpm * t
            self._phase_mot += 2.0 * math.pi * (40.0 + thr * 30.0) * t
            prop = math.sin(self._phase_prop) * 0.22 * thr * a.engine
            mot = math.sin(self._phase_mot) * 0.08 * thr * a.engine
            wind = (0.04 + 0.18 * spd) * a.wind * math.sin(self._phase_prop * 0.17)
            hangar = 0.02 * a.environment if self.scene == "hangar" else 0.0
            sample = (prop + mot + wind + hangar) * master
            sample = max(-0.95, min(0.95, sample))
            buf += struct.pack("<h", int(sample * 32767))
        try:
            self._io.write(bytes(buf))
        except Exception:  # noqa: BLE001
            self.stop()
