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
from dmi.mission_score import MissionScoreWeights  # noqa: E402


def _synth(
    n: int,
    n_agents: int,
    n_sectors: int,
    max_d: float,
    seed: int,
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    """Vectorized teacher labels. Argmax over sectors == nearest (soc/pay/health constant per agent)."""
    rng = np.random.default_rng(seed)
    agents = np.zeros((n, n_agents, 9), dtype=np.float32)
    sectors = np.zeros((n, n_sectors, 8), dtype=np.float32)
    agents[:, :, 0] = rng.uniform(-200, 200, (n, n_agents))
    agents[:, :, 1] = rng.uniform(-200, 200, (n, n_agents))
    agents[:, :, 2] = 50.0
    agents[:, :, 3] = rng.uniform(0.2, 1.0, (n, n_agents))
    agents[:, :, 4] = rng.uniform(0.0, 0.5, (n, n_agents))
    agents[:, :, 5] = rng.uniform(0.4, 1.0, (n, n_agents))
    agents[:, :, 8] = 1.0
    sectors[:, :, 0] = rng.uniform(-200, 200, (n, n_sectors))
    sectors[:, :, 1] = rng.uniform(-200, 200, (n, n_sectors))
    sectors[:, :, 2] = 50.0
    dx = agents[:, :, None, 0] - sectors[:, None, :, 0]
    dy = agents[:, :, None, 1] - sectors[:, None, :, 1]
    dist = np.hypot(dx, dy)
    d_hat = np.clip(dist / max_d, 0.0, 1.0)
    w = MissionScoreWeights()
    scores = (
        w.w_distance * (1.0 - d_hat)
        + w.w_soc * agents[:, :, None, 3]
        + w.w_payload * (1.0 - agents[:, :, None, 4])
        + w.w_health * agents[:, :, None, 5]
    ).astype(np.float32)
    return torch.from_numpy(agents), torch.from_numpy(sectors), torch.from_numpy(scores)


def _argmax_match(pred: torch.Tensor, teacher: torch.Tensor) -> float:
    return float((pred.argmax(-1) == teacher.argmax(-1)).float().mean().item())


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
    n_tr = int(cfg["samples"])
    n_va = int(cfg.get("val_samples", 512))
    agents, sectors, scores = _synth(
        n_tr,
        int(cfg["n_agents"]),
        int(cfg["n_sectors"]),
        float(cfg["max_distance_m"]),
        seed=0,
    )
    va_a, va_s, va_y = _synth(
        n_va,
        int(cfg["n_agents"]),
        int(cfg["n_sectors"]),
        float(cfg["max_distance_m"]),
        seed=1,
    )
    agents, sectors, scores = agents.to(device), sectors.to(device), scores.to(device)
    va_a, va_s, va_y = va_a.to(device), va_s.to(device), va_y.to(device)
    opt = torch.optim.Adam(model.parameters(), lr=float(cfg["lr"]))
    ce = torch.nn.CrossEntropyLoss()
    bs = int(cfg["batch_size"])
    gate = float(cfg.get("val_match_gate", 0.90))
    best_match = -1.0
    best_state = None
    model.train()
    for epoch in range(int(cfg["epochs"])):
        perm = torch.randperm(agents.shape[0], device=device)
        total = 0.0
        steps = 0
        for i in range(0, agents.shape[0], bs):
            idx = perm[i : i + bs]
            pred = model(agents[idx], sectors[idx])
            # CE only: MSE on 0–1 teacher scores pins logits → softmax ≈ uniform → log(32).
            labels = scores[idx].argmax(-1).reshape(-1)
            loss = ce(pred.reshape(-1, pred.shape[-1]), labels)
            opt.zero_grad()
            loss.backward()
            opt.step()
            total += float(loss.item())
            steps += 1
        model.eval()
        with torch.no_grad():
            vpred = model(va_a, va_s)
            match = _argmax_match(vpred, va_y)
        model.train()
        if match > best_match:
            best_match = match
            best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
        if epoch == 0 or (epoch + 1) % 10 == 0 or match >= gate:
            print(
                f"epoch={epoch+1} loss={total/max(steps,1):.4f} "
                f"val_argmax_match={match:.4f} best={best_match:.4f}"
            )
        if best_match >= gate and epoch + 1 >= 20:
            print(f"gate {gate} hit — stop")
            break
    if best_state is None:
        raise RuntimeError("BLOCKED: no weights")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    torch.save(best_state, args.out)
    print(f"wrote {args.out} best_val_argmax_match={best_match:.4f}")
    if best_match < gate:
        print(f"CANDIDATE FAIL gate={gate}", file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
