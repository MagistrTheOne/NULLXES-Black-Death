#!/usr/bin/env python3
"""Bake POSEIDON-VE-01 concept bank from Qwen/Qwen3-VL-Embedding-2B.

Product pack_id is always poseidon_ve_emb_2b (never Hub brand).
Requires image torch + sentence-transformers on train host.
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

import numpy as np
import yaml

REPO = Path(__file__).resolve().parents[4]


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--config",
        default=str(REPO / "06_autonomy/models/poseidon/configs/ve/emb_2b.yaml"),
    )
    ap.add_argument("--device", default="cuda")
    args = ap.parse_args()

    with open(args.config, encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}
    pack_id = str(cfg.get("pack_id", "poseidon_ve_emb_2b"))
    if pack_id != "poseidon_ve_emb_2b":
        print(f"BLOCKED: pack_id must be poseidon_ve_emb_2b, got {pack_id}")
        return 1
    product = str(cfg.get("product_name", "POSEIDON-VE-01"))
    if not product.startswith("POSEIDON-"):
        print(f"BLOCKED: product_name={product}")
        return 1
    base_repo = str(cfg.get("base_repo", "Qwen/Qwen3-VL-Embedding-2B"))
    concepts_rel = str(
        cfg.get("concepts_source", "06_autonomy/models/poseidon/concepts/civil_v1.yaml")
    )
    concepts_path = REPO / concepts_rel
    pack_dir = REPO / "06_autonomy/models/poseidon/packs" / pack_id
    pack_yaml = pack_dir / "pack.yaml"
    if not pack_yaml.is_file():
        print(f"BLOCKED: missing {pack_yaml}")
        return 1

    with open(concepts_path, encoding="utf-8") as f:
        crow = yaml.safe_load(f) or {}
    concepts = [str(c) for c in (crow.get("concepts") or [])]
    if not concepts:
        print("BLOCKED: empty concept list")
        return 1

    try:
        import torch
        from sentence_transformers import SentenceTransformer
    except ImportError as exc:
        print(f"BLOCKED: need torch+sentence_transformers on image: {exc}")
        return 1

    print(f"load {base_repo} → encode {len(concepts)} concepts → {pack_id}")
    model = SentenceTransformer(base_repo, device=args.device)
    emb = np.asarray(model.encode(concepts), dtype=np.float16)
    npy_path = pack_dir / "concepts.fp16.npy"
    np.save(npy_path, emb)

    # Optional: export ONNX later; for now pin bank sha into pack.yaml
    digest = _sha256(npy_path)
    with open(pack_yaml, encoding="utf-8") as f:
        pack = yaml.safe_load(f) or {}
    pack["product_name"] = product
    pack["base_repo"] = base_repo
    pack["dataset_hash"] = digest[:16]
    pack["emb_dim"] = int(emb.shape[1])
    pack["classes"] = concepts
    pack["validation_status"] = "bank_baked"
    # Keep sha256 pending until model.onnx export; bank is production artifact.
    with open(pack_yaml, "w", encoding="utf-8") as f:
        yaml.safe_dump(pack, f, sort_keys=False, allow_unicode=True)

    meta = pack_dir / "BANK.md"
    meta.write_text(
        f"# {product}\n\n"
        f"- pack_id: `{pack_id}`\n"
        f"- base_repo: `{base_repo}`\n"
        f"- concepts: {len(concepts)}\n"
        f"- emb_dim: {emb.shape[1]}\n"
        f"- bank: `concepts.fp16.npy` sha256={digest}\n"
        f"- SoftBus model field: `{product}`\n",
        encoding="utf-8",
    )
    print(f"OK baked {npy_path} shape={emb.shape} sha256={digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
