"""Envelope-gated NULLXES announcer. GSC only. No GoalMsg, no L0."""

from __future__ import annotations

import zlib
from dataclasses import dataclass
from pathlib import Path

import yaml

PACK_PATH = Path(__file__).resolve().parent / "pack.yaml"


@dataclass(frozen=True)
class VoiceCue:
    text: str
    sfx: str
    kind: str
    object_id: str
    envelope: str
    stamp_s: float


def _as_lines(raw: object) -> list[str]:
    if raw is None:
        return []
    if isinstance(raw, list):
        return [str(x) for x in raw if str(x).strip()]
    s = str(raw).strip()
    return [s] if s else []


def pick_line(lines: list[str], seed: str) -> str:
    if not lines:
        return ""
    idx = zlib.crc32(seed.encode("utf-8")) % len(lines)
    return lines[idx]


@dataclass(frozen=True)
class VoicePack:
    persona: str
    cooldown_s: float
    tts: str
    cloud_tts: bool
    civil_boot: str
    defense_boot: str
    defense_sting: str
    civil_lines: dict[str, list[str]]
    defense_lines: dict[str, list[str]]

    def line(self, envelope: str, kind: str, *, seed: str) -> str:
        table = self.defense_lines if envelope == "defense" else self.civil_lines
        if kind in table:
            lines = table[kind]
        else:
            lines = table.get("default") or []
        return pick_line(lines, f"{envelope}:{kind}:{seed}")


def load_voice_pack(path: Path | None = None) -> VoicePack:
    raw = yaml.safe_load((path or PACK_PATH).read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("invalid voice pack")
    if bool(raw.get("cloud_tts", False)):
        raise ValueError("cloud_tts forbidden")
    tts = str(raw.get("tts", "local_onnx"))
    if tts not in ("local_onnx", "sapi"):
        raise ValueError("tts must be local_onnx or sapi")
    civil = raw.get("civil") or {}
    defense = raw.get("defense") or {}
    return VoicePack(
        persona=str(raw.get("persona", "NULLXES")),
        cooldown_s=float(raw.get("cooldown_s", 12.0)),
        tts=tts,
        cloud_tts=False,
        civil_boot=str(civil.get("boot", "")),
        defense_boot=str(defense.get("boot", "")),
        defense_sting=str(defense.get("sting", "defense_sting")),
        civil_lines={str(k): _as_lines(v) for k, v in (civil.get("lines") or {}).items()},
        defense_lines={str(k): _as_lines(v) for k, v in (defense.get("lines") or {}).items()},
    )


class VoiceDirector:
    def __init__(self, pack: VoicePack | None = None) -> None:
        self.pack = pack or load_voice_pack()
        self.envelope = "civil"
        self._armed = False
        self._last: dict[tuple[str, str, str], float] = {}

    def on_envelope(self, envelope: str, *, stamp_s: float) -> VoiceCue | None:
        env = "defense" if str(envelope).lower() == "defense" else "civil"
        if env == self.envelope and self._armed:
            return None
        self.envelope = env
        self._armed = True
        if env == "defense":
            return VoiceCue(
                text=self.pack.defense_boot,
                sfx=self.pack.defense_sting,
                kind="envelope",
                object_id="",
                envelope=env,
                stamp_s=stamp_s,
            )
        return VoiceCue(
            text=self.pack.civil_boot,
            sfx="",
            kind="envelope",
            object_id="",
            envelope=env,
            stamp_s=stamp_s,
        )

    def on_detect(self, kind: str, object_id: str, *, stamp_s: float) -> VoiceCue | None:
        key = (self.envelope, kind, object_id)
        last = self._last.get(key, -1.0e9)
        if stamp_s - last < self.pack.cooldown_s:
            return None
        text = self.pack.line(self.envelope, kind, seed=object_id)
        if not text:
            return None
        self._last[key] = stamp_s
        return VoiceCue(
            text=text,
            sfx="",
            kind=kind,
            object_id=object_id,
            envelope=self.envelope,
            stamp_s=stamp_s,
        )

    def on_territorial(self, affiliation: str, track_id: str, *, stamp_s: float) -> VoiceCue | None:
        if self.envelope != "defense":
            return None
        kind = "territorial_friend" if affiliation == "friend" else "territorial_unknown"
        return self.on_detect(kind, track_id, stamp_s=stamp_s)
