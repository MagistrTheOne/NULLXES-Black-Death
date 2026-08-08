"""POSEIDON semantic layer — VE → optional RR → VL (event-driven). No Guidance."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from soft_bus.messages import ConceptHit, SceneFact

from .fw.gsc_client import PoseidonFwGscClient
from .pack_spec import PackSpec, PackSpecError, load_pack_spec
from .router import PoseidonRouter, RouterConfig, RouterContext, load_router_config
from .ve.engine import PoseidonVeEngine, apply_concept_hit_attrs
from .ve.rerank import PoseidonVeReranker
from .vl.scenefact import PoseidonVlEngine


@dataclass
class SemanticStepResult:
    hits: list[ConceptHit] = field(default_factory=list)
    scene: SceneFact | None = None
    ve_margin: float = 1.0
    selected_ve: list[str] = field(default_factory=list)
    selected_vl: list[str] = field(default_factory=list)


class PoseidonSemanticRuntime:
    def __init__(
        self,
        *,
        packs_root: Path,
        router_yaml: Path,
        repo_root: Path,
    ) -> None:
        self.packs_root = Path(packs_root)
        self.repo_root = Path(repo_root)
        self.specs: dict[str, PackSpec] = {}
        self.ve: PoseidonVeEngine | None = None
        self.rr: PoseidonVeReranker | None = None
        self.vl: PoseidonVlEngine | None = None
        self.fw: PoseidonFwGscClient | None = None

        for p in sorted(self.packs_root.iterdir()):
            yml = p / "pack.yaml"
            if not yml.is_file():
                continue
            try:
                spec = load_pack_spec(yml, verify_sha=True)
            except PackSpecError:
                continue
            if not spec.companion_load and spec.family != "fw":
                continue
            self.specs[spec.pack_id] = spec
            if spec.pack_id == "poseidon_ve_emb_2b":
                self.ve = PoseidonVeEngine(
                    spec, pack_dir=p, repo_root=self.repo_root
                )
            elif spec.pack_id == "poseidon_ve_rr_2b":
                self.rr = PoseidonVeReranker(spec)
            elif spec.pack_id == "poseidon_vl_scenefact_2b":
                self.vl = PoseidonVlEngine(spec)
            elif spec.pack_id == "poseidon_fw_gsc":
                # GSC only — construct for ground tools, never companion step
                try:
                    self.fw = PoseidonFwGscClient(spec)
                except RuntimeError:
                    self.fw = None

        cfg: RouterConfig = load_router_config(router_yaml)
        # FW never in companion available set
        avail = [k for k, s in self.specs.items() if s.companion_load]
        self.router = PoseidonRouter(cfg, avail)

    def step_roi(
        self,
        bgr: np.ndarray,
        ctx: RouterContext,
        *,
        object_id: str,
        track_id: int,
        trace_id: str = "",
        stamp_ns: int = 0,
        context: str = "",
    ) -> SemanticStepResult:
        selected_ve = self.router.select_ve(ctx)
        hits: list[ConceptHit] = []
        margin = 1.0
        ranked: list[tuple[str, float]] = []
        hit: ConceptHit | None = None

        if self.ve is not None and "poseidon_ve_emb_2b" in selected_ve:
            hit, margin, ranked = self.ve.match(
                bgr,
                object_id=object_id,
                track_id=track_id,
                trace_id=trace_id,
                stamp_ns=stamp_ns,
            )
            if hit is not None:
                hits.append(hit)

        ctx2 = RouterContext(
            mission_mode=ctx.mission_mode,
            cerber_cls_ids=ctx.cerber_cls_ids,
            cerber_max_conf=ctx.cerber_max_conf,
            link_ok=ctx.link_ok,
            has_unknown=ctx.has_unknown,
            unknown_conf=ctx.unknown_conf,
            cv_disagreement=ctx.cv_disagreement,
            ve_top_margin=margin,
            ve_miss=hit is None,
        )
        if (
            hit is not None
            and self.rr is not None
            and self.rr.ready
            and "poseidon_ve_rr_2b" in self.router.select_ve(ctx2)
        ):
            hit = self.rr.rerank(bgr, ranked, hit)
            hits = [hit]

        selected_vl = self.router.select_vl(ctx2)
        scene: SceneFact | None = None
        if self.vl is not None and selected_vl and self.vl.ready:
            scene = self.vl.infer_scenefact(
                bgr, context=context, trace_id=trace_id, stamp_ns=stamp_ns
            )

        return SemanticStepResult(
            hits=hits,
            scene=scene,
            ve_margin=margin,
            selected_ve=selected_ve,
            selected_vl=selected_vl,
        )


# re-export for attrs merge
__all__ = [
    "PoseidonSemanticRuntime",
    "SemanticStepResult",
    "apply_concept_hit_attrs",
]
