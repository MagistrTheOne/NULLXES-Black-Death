"""Train ATLAS-ALLOC on Mission Score teacher (synthetic AgentStatus × Sector)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import torch
import yaml

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from atlas.nn.bipartite import BipartiteAlloc  # noqa: E402
from dmi.mission_score import AgentScoreInput, score_agent  # noqa: E402


def _synth(n: int, n_agents: int, n_sectors: int, max_d: float) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    agents = np.zeros((n, n_agents, 9), dtype=np.float32)
    sectors = np.zeros((n, n_sectors, 8), dtype=np.float32)
    scores = np.zeros((n, n_agents, n_sectors), dtype=np.float32)
    rng = np.random.default_rng(0)
    for i in range(n):
        for a in range(n_agents):
            ax, ay = rng.uniform(-200, 200, 2)
            soc = float(rng.uniform(0.2, 1.0))
            pay = float(rng.uniform(0.0, 0.5))
            h = float(rng.uniform(0.4, 1.0))
            agents[i, a] = [ax, ay, 50.0, soc, pay, h, 0, 0, 1]
        for s in range(n_sectors):
            sx, sy = rng.uniform(-200, 200, 2)
            sectors[i, s] = [sx, sy, 50.0, 0, 0, 0, 0, 0]
            for a in range(n_agents):
                dist = float(np.hypot(agents[i, a, 0] - sx, agents[i, a, 1] - sy))
                inp = AgentScoreInput(
                    agent_id=str(a),
                    distance_m=dist,
                    soc=float(agents[i, a, 3]),
                    payload_frac=float(agents[i, a, 4]),
                    health_factor=float(agents[i, a, 5]),
                )
                scores[i, a, s] = score_agent(inp, max_distance_m=max_d)
    return torch.from_numpy(agents), torch.from_numpy(sectors), torch.from_numpy(scores)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--config", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    cfg = yaml.safe_load(args.config.read_text(encoding="utf-8"))
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"device={device}")
    model = BipartiteAlloc(
        agent_dim=int(cfg["agent_dim"]),
        sector_dim=int(cfg["sector_dim"]),
        hidden=int(cfg["hidden"]),
    ).to(device)
    agents, sectors, scores = _synth(
        int(cfg["samples"]),
        int(cfg["n_agents"]),
        int(cfg["n_sectors"]),
        float(cfg["max_distance_m"]),
    )
    agents, sectors, scores = agents.to(device), sectors.to(device), scores.to(device)
    opt = torch.optim.Adam(model.parameters(), lr=float(cfg["lr"]))
    loss_fn = torch.nn.MSELoss()
    model.train()
    bs = int(cfg["batch_size"])
    for _epoch in range(int(cfg["epochs"])):
        for i in range(0, agents.shape[0], bs):
            pred = model(agents[i : i + bs], sectors[i : i + bs])
            loss = loss_fn(pred, scores[i : i + bs])
            opt.zero_grad()
            loss.backward()
            opt.step()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    torch.save(model.state_dict(), args.out)
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
