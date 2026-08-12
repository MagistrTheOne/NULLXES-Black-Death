"""Export ATLAS-ALLOC PyTorch weights → ONNX (opset 17)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import torch
import yaml

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from atlas.nn.bipartite import BipartiteAlloc  # noqa: E402


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--config", type=Path, required=True)
    p.add_argument("--weights", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    cfg = yaml.safe_load(args.config.read_text(encoding="utf-8"))
    model = BipartiteAlloc(
        agent_dim=int(cfg["agent_dim"]),
        sector_dim=int(cfg["sector_dim"]),
        hidden=int(cfg["hidden"]),
    )
    model.load_state_dict(torch.load(args.weights, map_location="cpu"))
    model.eval()
    n, m = int(cfg["n_agents"]), int(cfg["n_sectors"])
    dummy_a = torch.zeros(1, n, int(cfg["agent_dim"]))
    dummy_s = torch.zeros(1, m, int(cfg["sector_dim"]))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    torch.onnx.export(
        model,
        (dummy_a, dummy_s),
        str(args.out),
        opset_version=17,
        input_names=["agents", "sectors"],
        output_names=["scores"],
        dynamic_axes={"agents": {0: "B"}, "sectors": {0: "B"}, "scores": {0: "B"}},
    )
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
