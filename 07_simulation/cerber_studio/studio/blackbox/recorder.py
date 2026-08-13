"""BLACKBOX product recorder — vehicle state at 20 Hz. Not TRACE_SPEC."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import yaml

from ..config.paths import user_dir

HZ = 20.0


def blackbox_root() -> Path:
    path = user_dir() / "BLACKBOX"
    path.mkdir(parents=True, exist_ok=True)
    return path


def new_flight_dir() -> Path:
    day = datetime.now().strftime("%Y-%m-%d")
    parent = blackbox_root() / day
    parent.mkdir(parents=True, exist_ok=True)
    n = 1
    while True:
        path = parent / f"flight_{n:04d}"
        if not path.exists():
            path.mkdir(parents=True)
            return path
        n += 1


class FlightRecorder:
    def __init__(self) -> None:
        self.dir: Path | None = None
        self._pose = None
        self._events = None
        self._acc = 0.0
        self.active = False
        self.meta: dict = {}

    def start(self, meta: dict) -> Path:
        self.close()
        self.dir = new_flight_dir()
        self.meta = dict(meta)
        self.meta["started"] = datetime.now(timezone.utc).isoformat()
        (self.dir / "meta.yaml").write_text(yaml.safe_dump(self.meta, allow_unicode=True), encoding="utf-8")
        self._pose = (self.dir / "pose.jsonl").open("a", encoding="utf-8")
        self._events = (self.dir / "events.jsonl").open("a", encoding="utf-8")
        self._acc = 0.0
        self.active = True
        self.event("START", meta)
        return self.dir

    def event(self, kind: str, payload: dict | None = None, t: float | None = None) -> None:
        if self._events is None:
            return
        row = {"t": float(t if t is not None else self.meta.get("t", 0.0)), "kind": kind, "payload": payload or {}}
        self._events.write(json.dumps(row) + "\n")
        self._events.flush()

    def tick(self, dt: float, sample: dict) -> bool:
        if not self.active or self._pose is None:
            return False
        self._acc += dt
        step = 1.0 / HZ
        if self._acc < step:
            return False
        self._acc -= step
        self.meta["t"] = float(sample.get("t", 0.0))
        self._pose.write(json.dumps(sample) + "\n")
        return True

    def close(self) -> None:
        if self._pose is not None:
            self._pose.close()
            self._pose = None
        if self._events is not None:
            self._events.close()
            self._events = None
        if self.dir is not None and self.meta:
            self.meta["ended"] = datetime.now(timezone.utc).isoformat()
            (self.dir / "meta.yaml").write_text(yaml.safe_dump(self.meta, allow_unicode=True), encoding="utf-8")
        self.active = False


def load_replay(path: Path) -> tuple[dict, list[dict], list[dict]]:
    meta: dict = {}
    mp = path / "meta.yaml"
    if mp.is_file():
        meta = yaml.safe_load(mp.read_text(encoding="utf-8")) or {}
    poses: list[dict] = []
    pf = path / "pose.jsonl"
    if pf.is_file():
        for line in pf.read_text(encoding="utf-8").splitlines():
            if line.strip():
                poses.append(json.loads(line))
    events: list[dict] = []
    ef = path / "events.jsonl"
    if ef.is_file():
        for line in ef.read_text(encoding="utf-8").splitlines():
            if line.strip():
                events.append(json.loads(line))
    return meta, poses, events
