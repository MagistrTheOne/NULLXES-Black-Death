"""BLACKBOX product recorder — vehicle state at 20 Hz. Not TRACE_SPEC."""

from __future__ import annotations

import json
import logging
import queue
import threading
from datetime import datetime, timezone
from pathlib import Path

import yaml

from ..config.paths import user_dir

log = logging.getLogger("cerber_studio.blackbox")

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
        self.dropped = 0
        self._q: queue.Queue = queue.Queue(maxsize=64)
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self, meta: dict) -> Path:
        self.close()
        self.dir = new_flight_dir()
        self.meta = dict(meta)
        self.meta["started"] = datetime.now(timezone.utc).isoformat()
        (self.dir / "meta.yaml").write_text(yaml.safe_dump(self.meta, allow_unicode=True), encoding="utf-8")
        self._pose = (self.dir / "pose.jsonl").open("a", encoding="utf-8")
        self._events = (self.dir / "events.jsonl").open("a", encoding="utf-8")
        self._acc = 0.0
        self.dropped = 0
        self.active = True
        self._stop.clear()
        self._q = queue.Queue(maxsize=64)
        self._thread = threading.Thread(target=self._writer, name="blackbox-writer", daemon=True)
        self._thread.start()
        self.event("START", meta)
        return self.dir

    def event(self, kind: str, payload: dict | None = None, t: float | None = None) -> None:
        if not self.active:
            return
        row = {"t": float(t if t is not None else self.meta.get("t", 0.0)), "kind": kind, "payload": payload or {}}
        self._enqueue(("event", row))

    def tick(self, dt: float, sample: dict) -> bool:
        if not self.active:
            return False
        self._acc += dt
        step = 1.0 / HZ
        if self._acc < step:
            return False
        self._acc -= step
        self.meta["t"] = float(sample.get("t", 0.0))
        return self._enqueue(("pose", sample))

    def _enqueue(self, item) -> bool:
        try:
            self._q.put_nowait(item)
            return True
        except queue.Full:
            try:
                self._q.get_nowait()
            except queue.Empty:
                pass
            self.dropped += 1
            if self.dropped == 1 or self.dropped % 50 == 0:
                log.warning("recorder dropped samples count=%s", self.dropped)
            try:
                self._q.put_nowait(item)
                return True
            except queue.Full:
                return False

    def _writer(self) -> None:
        while not self._stop.is_set() or not self._q.empty():
            try:
                kind, payload = self._q.get(timeout=0.1)
            except queue.Empty:
                continue
            try:
                line = json.dumps(payload) + "\n"
                if kind == "pose" and self._pose is not None:
                    self._pose.write(line)
                elif kind == "event" and self._events is not None:
                    self._events.write(line)
            except Exception as exc:
                log.warning("recorder write: %s", exc)

    def close(self) -> None:
        self.active = False
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=1.5)
            self._thread = None
        if self._pose is not None:
            try:
                self._pose.flush()
                self._pose.close()
            except Exception:
                pass
            self._pose = None
        if self._events is not None:
            try:
                self._events.flush()
                self._events.close()
            except Exception:
                pass
            self._events = None
        if self.dir is not None and self.meta:
            self.meta["ended"] = datetime.now(timezone.utc).isoformat()
            self.meta["dropped_samples"] = self.dropped
            (self.dir / "meta.yaml").write_text(yaml.safe_dump(self.meta, allow_unicode=True), encoding="utf-8")


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
