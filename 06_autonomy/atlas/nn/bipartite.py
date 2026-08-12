"""NULLXES ATLAS-ALLOC bipartite scorer — DeepSets + cross-score. Own weights."""

from __future__ import annotations

import torch
from torch import nn


class BipartiteAlloc(nn.Module):
    def __init__(self, agent_dim: int = 9, sector_dim: int = 8, hidden: int = 32) -> None:
        super().__init__()
        self.agent_enc = nn.Sequential(
            nn.Linear(agent_dim, hidden),
            nn.ReLU(),
            nn.Linear(hidden, hidden),
        )
        self.sector_enc = nn.Sequential(
            nn.Linear(sector_dim, hidden),
            nn.ReLU(),
            nn.Linear(hidden, hidden),
        )
        self.score = nn.Linear(hidden * 2, 1)

    def forward(self, agents: torch.Tensor, sectors: torch.Tensor) -> torch.Tensor:
        """agents [B,N,Fa], sectors [B,M,Fs] → scores [B,N,M]."""
        ae = self.agent_enc(agents)
        se = self.sector_enc(sectors)
        n, m = ae.shape[1], se.shape[1]
        ae_e = ae.unsqueeze(2).expand(-1, n, m, -1)
        se_e = se.unsqueeze(1).expand(-1, n, m, -1)
        cat = torch.cat([ae_e, se_e], dim=-1)
        return self.score(cat).squeeze(-1)
