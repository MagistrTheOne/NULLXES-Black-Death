#!/usr/bin/env python3
"""Fail-closed POSEIDON pack verification for companion image."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import yaml


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--pack",
        type=Path,
        default=Path(__file__).resolve().parents[1]
        / "models"
        / "poseidon"
        / "packs"
        / "uav_seraphim",
    )
    args = ap.parse_args()
    manifest = args.pack / "pack.yaml"
    if not manifest.is_file():
        print(json.dumps({"ok": False, "error": "missing pack.yaml"}))
        return 2
    raw = yaml.safe_load(manifest.read_text(encoding="utf-8"))
    model = args.pack / str(raw.get("model_path", "model.onnx"))
    expected = str(raw.get("sha256", "pending"))
    if not model.is_file():
        print(
            json.dumps(
                {
                    "ok": False,
                    "pack_id": raw.get("pack_id"),
                    "error": "model.onnx missing — train/export required",
                    "sha256_manifest": expected,
                }
            )
        )
        return 1
    digest = hashlib.sha256(model.read_bytes()).hexdigest()
    ok = expected not in ("", "pending") and digest == expected
    print(
        json.dumps(
            {
                "ok": ok,
                "pack_id": raw.get("pack_id"),
                "sha256": digest,
                "sha256_manifest": expected,
                "match": digest == expected,
            },
            indent=2,
        )
    )
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
