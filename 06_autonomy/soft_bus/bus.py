"""In-process soft bus — canon topic names from ALPHA_5x5_ROS_TOPICS."""

from __future__ import annotations

import threading
from collections import defaultdict, deque
from typing import Any, Callable


class SoftBus:
    """Thread-safe pub/sub. Nested publish is queued (no reentrancy recursion)."""

    def __init__(self) -> None:
        self._subs: dict[str, list[Callable[[Any], None]]] = defaultdict(list)
        self._latest: dict[str, Any] = {}
        self._lock = threading.RLock()
        self._queue: deque[tuple[str, Any]] = deque()
        self._draining = False

    def publish(self, topic: str, msg: Any) -> None:
        with self._lock:
            self._latest[topic] = msg
            self._queue.append((topic, msg))
            if self._draining:
                return
            self._draining = True
        try:
            while True:
                with self._lock:
                    if not self._queue:
                        self._draining = False
                        return
                    t, m = self._queue.popleft()
                    cbs = list(self._subs.get(t, []))
                for cb in cbs:
                    cb(m)
        finally:
            with self._lock:
                self._draining = False

    def subscribe(self, topic: str, callback: Callable[[Any], None]) -> None:
        with self._lock:
            self._subs[topic].append(callback)

    def latest(self, topic: str, default: Any = None) -> Any:
        with self._lock:
            return self._latest.get(topic, default)

    def unsubscribe_all(self, topic: str | None = None) -> None:
        with self._lock:
            if topic is None:
                self._subs.clear()
            else:
                self._subs.pop(topic, None)
