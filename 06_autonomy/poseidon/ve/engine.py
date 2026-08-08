"""POSEIDON-VE-01 — Hub load Qwen/Qwen3-VL-Embedding-2B + civil concept bank."""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import yaml

from soft_bus.messages import ConceptHit

from poseidon.pack_spec import PackSpec


def apply_concept_hit_attrs(attrs: dict[str, str], hit: ConceptHit) -> dict[str, str]:
    out = dict(attrs)
    out["ve_concept"] = hit.concept
    out["ve_score"] = f"{hit.score:.4f}"
    out["ve_model"] = hit.model
    if hit.reranker:
        out["ve_reranker"] = hit.reranker
    return out


@dataclass
class ConceptBank:
    names: tuple[str, ...]
    embeddings: np.ndarray  # [N, D] float32 L2-normalized

    @classmethod
    def from_npy(cls, npy_path: Path, names: tuple[str, ...]) -> "ConceptBank":
        emb = np.load(npy_path).astype(np.float32)
        if emb.ndim != 2 or emb.shape[0] != len(names):
            raise ValueError(
                f"concept bank shape {emb.shape} != names={len(names)}"
            )
        emb = _l2_normalize(emb)
        return cls(names=names, embeddings=emb)

    @classmethod
    def from_concepts_yaml(
        cls, concepts_yaml: Path, embeddings: np.ndarray
    ) -> "ConceptBank":
        with open(concepts_yaml, encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}
        names = tuple(str(c) for c in (raw.get("concepts") or []))
        if not names:
            raise ValueError(f"empty concepts in {concepts_yaml}")
        return cls.from_npy_arrays(names, embeddings)

    @classmethod
    def from_npy_arrays(cls, names: tuple[str, ...], emb: np.ndarray) -> "ConceptBank":
        e = _l2_normalize(np.asarray(emb, dtype=np.float32))
        if e.shape[0] != len(names):
            raise ValueError("names/emb mismatch")
        return cls(names=names, embeddings=e)

    def topk(self, query: np.ndarray, k: int = 5) -> list[tuple[str, float]]:
        q = _l2_normalize(np.asarray(query, dtype=np.float32).reshape(1, -1))[0]
        sims = self.embeddings @ q
        idx = np.argsort(-sims)[:k]
        return [(self.names[i], float(sims[i])) for i in idx]


def _l2_normalize(x: np.ndarray) -> np.ndarray:
    n = np.linalg.norm(x, axis=-1, keepdims=True)
    n = np.maximum(n, 1e-12)
    return x / n


class PoseidonVeEngine:
    """Production VE: transformers_hub base_repo or baked concepts.fp16.npy + encoder."""

    def __init__(self, spec: PackSpec, *, pack_dir: Path, repo_root: Path) -> None:
        self.spec = spec
        self.pack_dir = Path(pack_dir)
        self.repo_root = Path(repo_root)
        self.product = spec.product_name or "POSEIDON-VE-01"
        self._model: Any = None
        self._bank: ConceptBank | None = None
        self._load_bank()
        if spec.load_from_hub and spec.base_repo:
            self._try_load_hub()

    @property
    def ready(self) -> bool:
        return self._bank is not None and (
            self._model is not None or self._bank.embeddings.size > 0
        )

    def _concepts_path(self) -> Path:
        if self.spec.concepts_source:
            p = Path(self.spec.concepts_source)
            if not p.is_absolute():
                p = self.repo_root / p
            return p
        return self.repo_root / "06_autonomy/models/poseidon/concepts/civil_v1.yaml"

    def _load_bank(self) -> None:
        npy = self.pack_dir / (self.spec.concept_bank_path or "concepts.fp16.npy")
        names = self.spec.classes
        if npy.is_file():
            self._bank = ConceptBank.from_npy(npy, names)
            return
        # Bank built at bake time; until then names-only bank is not usable for cosine.
        self._bank = None

    def _try_load_hub(self) -> None:
        try:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self.spec.base_repo)
            # If bank missing, encode concepts from civil_v1 / pack classes once.
            if self._bank is None:
                texts = list(self.spec.classes)
                cpath = self._concepts_path()
                if cpath.is_file():
                    with open(cpath, encoding="utf-8") as f:
                        raw = yaml.safe_load(f) or {}
                    texts = [str(c) for c in (raw.get("concepts") or texts)]
                emb = np.asarray(self._model.encode(texts), dtype=np.float32)
                self._bank = ConceptBank.from_npy_arrays(tuple(texts), emb)
        except Exception:
            self._model = None

    def encode_roi(self, bgr: np.ndarray) -> np.ndarray | None:
        if self._model is None:
            return None
        from PIL import Image
        import cv2

        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(rgb)
        # Qwen3-VL-Embedding via SentenceTransformer accepts image inputs when supported.
        try:
            vec = self._model.encode([img])
        except Exception:
            try:
                vec = self._model.encode_image([img])
            except Exception:
                return None
        return np.asarray(vec, dtype=np.float32).reshape(-1)

    def match(
        self,
        bgr: np.ndarray,
        *,
        object_id: str,
        track_id: int,
        trace_id: str = "",
        stamp_ns: int = 0,
        top_k: int = 5,
    ) -> tuple[ConceptHit | None, float, list[tuple[str, float]]]:
        """Returns (best_hit_or_None, top2_margin, topk)."""
        if self._bank is None:
            return None, 1.0, []
        t0 = time.perf_counter()
        q = self.encode_roi(bgr)
        if q is None:
            return None, 1.0, []
        ranked = self._bank.topk(q, k=top_k)
        if not ranked:
            return None, 1.0, []
        best_name, best_score = ranked[0]
        margin = 1.0
        if len(ranked) >= 2:
            margin = best_score - ranked[1][1]
        ms = (time.perf_counter() - t0) * 1000.0
        if ms > self.spec.budget_ms * 4:
            # Soft note only — still return; hard budget enforced by router rate.
            pass
        if best_score < self.spec.score_threshold:
            return None, margin, ranked
        hit = ConceptHit(
            object_id=object_id,
            track_id=track_id,
            concept=best_name,
            score=best_score,
            source="poseidon_ve",
            model=self.product,
            emb_dim=int(q.shape[0]),
            stamp_ns=stamp_ns,
            trace_id=trace_id,
        )
        return hit, margin, ranked
