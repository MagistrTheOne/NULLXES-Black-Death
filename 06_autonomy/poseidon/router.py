"""POSEIDON router v1 — mission/CERBER gates + pack budget (no LLM)."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class RouterContext:
    mission_mode: str = "NOMINAL"
    cerber_cls_ids: list[int] = field(default_factory=list)
    cerber_max_conf: dict[int, float] = field(default_factory=dict)
    link_ok: bool = True


@dataclass(frozen=True)
class RouterConfig:
    max_packs_per_frame: int
    priority: tuple[str, ...]
    gates: dict[str, Any]


def load_router_config(path: str | Path) -> RouterConfig:
    p = Path(path)
    with open(p, encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}
    priority = tuple(str(x) for x in (raw.get("priority") or []))
    return RouterConfig(
        max_packs_per_frame=int(raw.get("max_packs_per_frame", 1)),
        priority=priority,
        gates=dict(raw.get("gates") or {}),
    )


class PoseidonRouter:
    def __init__(self, cfg: RouterConfig, available_pack_ids: list[str]) -> None:
        self.cfg = cfg
        self.available = set(available_pack_ids)

    def select(self, ctx: RouterContext) -> list[str]:
        enabled: list[str] = []
        for pack_id in self.cfg.priority:
            if pack_id not in self.available:
                continue
            gate = self.cfg.gates.get(pack_id) or {}
            if self._gate_ok(pack_id, gate, ctx):
                enabled.append(pack_id)
            if len(enabled) >= self.cfg.max_packs_per_frame:
                break
        return enabled

    def _gate_ok(self, pack_id: str, gate: dict[str, Any], ctx: RouterContext) -> bool:
        always = bool(gate.get("always", False))
        if always:
            return True

        modes = gate.get("mission_modes")
        mode_ok = modes is None or ctx.mission_mode in {str(m) for m in modes}
        if not mode_ok:
            return False

        # Dedicated airspace / disaster modes run specialist without CERBER hint
        force_modes = {str(m) for m in (gate.get("force_mission_modes") or [])}
        if not force_modes:
            force_modes = {"AIRSPACE_GUARD", "DISASTER", "INFRA_INSPECT"}
        if ctx.mission_mode in force_modes and modes is not None:
            return True

        hint_cls = gate.get("cerber_hint_cls")
        if hint_cls is None:
            return True

        hints = {int(c) for c in hint_cls}
        min_conf = float(gate.get("cerber_hint_min_conf", 0.0))
        for c in hints:
            if c in ctx.cerber_cls_ids and ctx.cerber_max_conf.get(c, 0.0) >= min_conf:
                return True
        return False
