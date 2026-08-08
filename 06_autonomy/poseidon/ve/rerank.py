"""POSEIDON-VE-R01 — Hub load Qwen/Qwen3-VL-Reranker-2B."""

from __future__ import annotations

from typing import Any

import numpy as np

from soft_bus.messages import ConceptHit

from poseidon.pack_spec import PackSpec


class PoseidonVeReranker:
    def __init__(self, spec: PackSpec) -> None:
        self.spec = spec
        self.product = spec.product_name or "POSEIDON-VE-R01"
        self._model: Any = None
        if spec.load_from_hub and spec.base_repo:
            self._try_load()

    @property
    def ready(self) -> bool:
        return self._model is not None

    def _try_load(self) -> None:
        try:
            from sentence_transformers import CrossEncoder

            self._model = CrossEncoder(self.spec.base_repo)
        except Exception:
            try:
                from transformers import AutoModel

                self._model = AutoModel.from_pretrained(
                    self.spec.base_repo, trust_remote_code=True
                )
            except Exception:
                self._model = None

    def rerank(
        self,
        bgr: np.ndarray,
        candidates: list[tuple[str, float]],
        hit: ConceptHit,
    ) -> ConceptHit:
        if not candidates or self._model is None:
            return hit
        # CrossEncoder path: (image_desc, concept) pairs — use concept text only if image
        # pair API unavailable; keep best cosine if score API fails.
        try:
            pairs = [["aerial roi", c] for c, _ in candidates]
            scores = self._model.predict(pairs)
            best_i = int(np.argmax(scores))
            name, _ = candidates[best_i]
            return ConceptHit(
                object_id=hit.object_id,
                track_id=hit.track_id,
                concept=name,
                score=float(scores[best_i]),
                source=hit.source,
                model=hit.model,
                emb_dim=hit.emb_dim,
                stamp_ns=hit.stamp_ns,
                trace_id=hit.trace_id,
                reranker=self.product,
            )
        except Exception:
            return ConceptHit(
                object_id=hit.object_id,
                track_id=hit.track_id,
                concept=hit.concept,
                score=hit.score,
                source=hit.source,
                model=hit.model,
                emb_dim=hit.emb_dim,
                stamp_ns=hit.stamp_ns,
                trace_id=hit.trace_id,
                reranker=self.product,
            )
