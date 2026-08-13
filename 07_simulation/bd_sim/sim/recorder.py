"""JSONL run recorder. One file per session."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, TextIO


class JsonlRecorder:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._fp: TextIO = self.path.open("w", encoding="utf-8")

    def write(self, row: dict[str, Any]) -> None:
        self._fp.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")

    def close(self) -> None:
        self._fp.close()
