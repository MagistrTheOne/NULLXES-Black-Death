#!/usr/bin/env python3
"""Validate POSEIDON registry + pack manifests (CI / server)."""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO / "06_autonomy"))

from poseidon.pack_spec import PackSpecError, load_pack_spec  # noqa: E402


def main() -> int:
    reg_path = (
        REPO / "06_autonomy" / "models" / "poseidon" / "registry" / "registry.yaml"
    )
    with open(reg_path, encoding="utf-8") as f:
        reg = yaml.safe_load(f)
    rejects = [str(x).lower() for x in (reg.get("civil_reject") or [])]
    errors = 0
    for entry in reg.get("poseidon_packs") or []:
        pack_id = entry["pack_id"]
        dataset = str(entry.get("dataset", "")).lower()
        for bad in rejects:
            if bad in dataset or bad in pack_id.lower():
                print(f"BLOCKED: civil reject pack={pack_id} dataset={dataset}")
                errors += 1
        manifest = REPO / entry["manifest"]
        try:
            spec = load_pack_spec(manifest, verify_sha=True)
            ch = entry.get("release_channel", spec.release_channel)
            print(
                f"OK pack={spec.pack_id} layout={spec.onnx_layout} "
                f"channel={ch} onnx={'yes' if spec.model_path.is_file() else 'pending'} "
                f"status={spec.validation_status}"
            )
        except PackSpecError as exc:
            print(f"BLOCKED: {exc}")
            errors += 1
    router = REPO / "06_autonomy" / "models" / "poseidon" / "router" / "router.yaml"
    if not router.is_file():
        print(f"BLOCKED: missing {router}")
        errors += 1
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
