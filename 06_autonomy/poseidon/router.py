"""POSEIDON router v2 — CV + VE/VL event gates (no LLM)."""

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
    # VE/VL triggers
    has_unknown: bool = False
    unknown_conf: float = 0.0
    cv_disagreement: bool = False
    ve_top_margin: float = 1.0
    ve_miss: bool = False


@dataclass(frozen=True)
class RouterConfig:
    max_packs_per_frame: int
    priority: tuple[str, ...]
    gates: dict[str, Any]
    max_ve_rois_per_frame: int = 4
    max_vl_calls_per_s: float = 2.0
    futureworld_on_companion: bool = False
    ve_unknown_conf_lo: float = 0.25
    ve_unknown_conf_hi: float = 0.55
    ve_margin_escalate: float = 0.08
    vl_escalate_on_ve_miss: bool = True
    ve_priority: tuple[str, ...] = ()
    vl_priority: tuple[str, ...] = ()
    ve_gates: dict[str, Any] = field(default_factory=dict)
    vl_gates: dict[str, Any] = field(default_factory=dict)


def load_router_config(path: str | Path) -> RouterConfig:
    p = Path(path)
    with open(p, encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}
    priority = tuple(str(x) for x in (raw.get("priority") or []))
    return RouterConfig(
        max_packs_per_frame=int(raw.get("max_packs_per_frame", 1)),
        priority=priority,
        gates=dict(raw.get("gates") or {}),
        max_ve_rois_per_frame=int(raw.get("max_ve_rois_per_frame", 4)),
        max_vl_calls_per_s=float(raw.get("max_vl_calls_per_s", 2.0)),
        futureworld_on_companion=bool(raw.get("futureworld_on_companion", False)),
        ve_unknown_conf_lo=float(raw.get("ve_unknown_conf_lo", 0.25)),
        ve_unknown_conf_hi=float(raw.get("ve_unknown_conf_hi", 0.55)),
        ve_margin_escalate=float(raw.get("ve_margin_escalate", 0.08)),
        vl_escalate_on_ve_miss=bool(raw.get("vl_escalate_on_ve_miss", True)),
        ve_priority=tuple(str(x) for x in (raw.get("ve_priority") or [])),
        vl_priority=tuple(str(x) for x in (raw.get("vl_priority") or [])),
        ve_gates=dict(raw.get("ve_gates") or {}),
        vl_gates=dict(raw.get("vl_gates") or {}),
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

    def select_ve(self, ctx: RouterContext) -> list[str]:
        out: list[str] = []
        for pack_id in self.cfg.ve_priority:
            if pack_id not in self.available:
                continue
            gate = self.cfg.ve_gates.get(pack_id) or {}
            if not self._mission_ok(gate, ctx):
                continue
            if pack_id.endswith("_rr_2b") or "rr" in pack_id:
                if bool(gate.get("on_ve_margin", True)) and ctx.ve_top_margin < self.cfg.ve_margin_escalate:
                    out.append(pack_id)
                continue
            need = False
            if bool(gate.get("on_unknown", True)) and ctx.has_unknown:
                lo, hi = self.cfg.ve_unknown_conf_lo, self.cfg.ve_unknown_conf_hi
                if lo <= ctx.unknown_conf <= hi or ctx.unknown_conf <= 0.0:
                    need = True
            if bool(gate.get("on_disagreement", True)) and ctx.cv_disagreement:
                need = True
            if need:
                out.append(pack_id)
        return out[: self.cfg.max_ve_rois_per_frame]

    def select_vl(self, ctx: RouterContext) -> list[str]:
        if not self.cfg.vl_escalate_on_ve_miss and not ctx.ve_miss:
            if ctx.ve_top_margin >= self.cfg.ve_margin_escalate:
                return []
        out: list[str] = []
        for pack_id in self.cfg.vl_priority:
            if pack_id not in self.available:
                continue
            gate = self.cfg.vl_gates.get(pack_id) or {}
            if not self._mission_ok(gate, ctx):
                continue
            if bool(gate.get("on_ve_escalate", True)) and (
                ctx.ve_miss or ctx.ve_top_margin < self.cfg.ve_margin_escalate or ctx.cv_disagreement
            ):
                out.append(pack_id)
        return out[:1]

    def _mission_ok(self, gate: dict[str, Any], ctx: RouterContext) -> bool:
        modes = gate.get("mission_modes")
        if modes is None:
            return True
        return ctx.mission_mode in {str(m) for m in modes}

    def _gate_ok(self, pack_id: str, gate: dict[str, Any], ctx: RouterContext) -> bool:
        always = bool(gate.get("always", False))
        if always:
            return True

        modes = gate.get("mission_modes")
        mode_ok = modes is None or ctx.mission_mode in {str(m) for m in modes}
        if not mode_ok:
            return False

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
