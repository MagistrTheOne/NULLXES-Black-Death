"""Pilot record — clearance, not XP."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path

import yaml

from .config.paths import user_dir


def record_path() -> Path:
    return user_dir() / "pilot_record.yaml"


@dataclass
class PilotRecord:
    flights: int = 0
    time_s: float = 0.0
    distance_m: float = 0.0
    level: int = 1
    follow_cleared: bool = False
    night_unlocked: bool = False
    landings_clean: int = 0
    last_grade: str = ""
    discovered: list = field(default_factory=list)
    certs: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def load(cls) -> PilotRecord:
        path = record_path()
        if not path.is_file():
            rec = cls()
            rec.save()
            return rec
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        known = {k: getattr(cls(), k) for k in cls().__dict__}
        known.update({k: data[k] for k in known if k in data})
        if not isinstance(known.get("discovered"), list):
            known["discovered"] = []
        if not isinstance(known.get("certs"), list):
            known["certs"] = []
        return cls(**known)

    def save(self) -> None:
        record_path().write_text(yaml.safe_dump(self.to_dict(), allow_unicode=True), encoding="utf-8")

    def apply_flight(self, *, time_s: float, distance_m: float, grade: str, mission_id: str) -> None:
        self.flights += 1
        self.time_s += float(time_s)
        self.distance_m += float(distance_m)
        self.last_grade = grade
        if grade == "CLEAN":
            self.landings_clean += 1
        if mission_id in ("target_follow",) or (mission_id and "follow" in mission_id):
            self.follow_cleared = True
            self.night_unlocked = True
        hours = self.time_s / 3600.0
        self.level = 1 + int(hours) + self.landings_clean // 3
        self.save()

    def discover(self, title: str) -> bool:
        if not title or title in self.discovered:
            return False
        self.discovered.append(title)
        self.save()
        return True

    def certify(self, name: str, grade: dict) -> None:
        self.certs.append({"name": name, **grade})
        if name.lower().replace(" ", "_") in ("target_follow", "follow"):
            self.follow_cleared = True
            self.night_unlocked = True
        self.save()
