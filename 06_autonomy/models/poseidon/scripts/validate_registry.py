#!/usr/bin/env python3
"""Validate POSEIDON registry + pack manifests (CI / server)."""

from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO / "06_autonomy"))

from poseidon.pack_spec import (  # noqa: E402
    PackSpecError,
    load_pack_spec,
    validate_pack_naming,
)

PACK_ID_RE = re.compile(
    r"^(uav_|fire_|power_|scene_|vehicle_|poseidon_)[a-z0-9_]+$"
)
FORBIDDEN = ("qwen", "siglip", "florence", "mobileclip")


def main() -> int:
    reg_path = (
        REPO / "06_autonomy" / "models" / "poseidon" / "registry" / "registry.yaml"
    )
    with open(reg_path, encoding="utf-8") as f:
        reg = yaml.safe_load(f)
    if int(reg.get("version", 0)) < 3:
        print("BLOCKED: registry version must be >= 3")
        return 1
    rejects = [str(x).lower() for x in (reg.get("civil_reject") or [])]
    errors = 0
    for entry in reg.get("poseidon_packs") or []:
        pack_id = str(entry["pack_id"])
        dataset = str(entry.get("dataset", "")).lower()
        family = str(entry.get("family", "")).strip().lower()
        product_name = str(entry.get("product_name", "")).strip()
        for bad in rejects:
            if bad in dataset or bad in pack_id.lower():
                print(f"BLOCKED: civil reject pack={pack_id} dataset={dataset}")
                errors += 1
        if family not in ("cv", "ve", "vl", "fw"):
            print(f"BLOCKED: registry family missing/invalid pack={pack_id}")
            errors += 1
        try:
            validate_pack_naming(pack_id, product_name)
        except PackSpecError as exc:
            print(f"BLOCKED: {exc}")
            errors += 1
        for bad in FORBIDDEN:
            if bad in pack_id.lower() or bad in product_name.lower():
                print(f"BLOCKED: hub brand in ids pack={pack_id} product={product_name}")
                errors += 1
        if not PACK_ID_RE.match(pack_id):
            print(f"BLOCKED: pack_id pattern pack={pack_id}")
            errors += 1
        manifest = REPO / entry["manifest"]
        try:
            spec = load_pack_spec(manifest, verify_sha=True)
            ch = entry.get("release_channel", spec.release_channel)
            print(
                f"OK pack={spec.pack_id} family={spec.family} "
                f"product={spec.product_name} layout={spec.onnx_layout} "
                f"channel={ch} onnx={'yes' if spec.model_path.is_file() else 'pending'} "
                f"companion={spec.companion_load} status={spec.validation_status}"
            )
        except PackSpecError as exc:
            print(f"BLOCKED: {exc}")
            errors += 1
    router = REPO / "06_autonomy" / "models" / "poseidon" / "router" / "router.yaml"
    if not router.is_file():
        print(f"BLOCKED: missing {router}")
        errors += 1
    concepts = (
        REPO / "06_autonomy" / "models" / "poseidon" / "concepts" / "civil_v1.yaml"
    )
    if not concepts.is_file():
        print(f"BLOCKED: missing {concepts}")
        errors += 1
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
