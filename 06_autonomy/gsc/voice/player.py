"""GSC audio sink. SAPI TTS + winsound sting. Fail-closed if no device."""

from __future__ import annotations

import queue
import subprocess
import sys
import threading
from pathlib import Path

from .director import VoiceCue
from .sting import write_defense_sting
from .tts_runtime import backend_id, load_onnx_session


class VoicePlayer:
    def __init__(self, *, enabled: bool = True) -> None:
        self.enabled = enabled
        self.backend = backend_id() if enabled else "none"
        self._session = load_onnx_session() if enabled else None
        self._q: queue.Queue[VoiceCue | None] = queue.Queue()
        self._sting_path: Path | None = None
        self._thread: threading.Thread | None = None
        if enabled:
            self._thread = threading.Thread(target=self._run, daemon=True, name="nullxes-voice")
            self._thread.start()

    def submit(self, cue: VoiceCue) -> None:
        if not self.enabled:
            return
        self._q.put(cue)

    def close(self) -> None:
        if not self.enabled:
            return
        self._q.put(None)

    def _run(self) -> None:
        while True:
            cue = self._q.get()
            if cue is None:
                return
            try:
                if cue.sfx == "defense_sting":
                    self._play_sting()
                if cue.text:
                    _speak(cue.text)
            except OSError:
                return

    def _play_sting(self) -> None:
        if self._sting_path is None or not self._sting_path.is_file():
            self._sting_path = write_defense_sting()
        if sys.platform == "win32":
            import winsound

            winsound.PlaySound(
                str(self._sting_path),
                winsound.SND_FILENAME | winsound.SND_ASYNC,
            )


def _speak(text: str) -> None:
    if sys.platform != "win32":
        return
    try:
        import pythoncom
        from win32com.client import Dispatch

        pythoncom.CoInitialize()
        voice = Dispatch("SAPI.SpVoice")
        voice.Rate = -1
        voice.Speak(text)
        return
    except Exception:
        pass
    escaped = text.replace("'", "''")
    subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-WindowStyle",
            "Hidden",
            "-Command",
            "Add-Type -AssemblyName System.Speech; "
            "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
            "$s.Rate = -1; "
            f"$s.Speak('{escaped}')",
        ],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
