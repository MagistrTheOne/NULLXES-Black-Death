# POSEIDON packs

Local specialist ONNX agents. Canon: `00_docs/architecture/POSEIDON.md` · ADR-005.

| Pack | Dataset | CERBER id |
|------|---------|-----------|
| `uav_seraphim` | Seraphim / DUT | `uav=2` |
| `fire_flame` | FLAME | `fire=10` |
| `power_insplad` | InsPLAD/MPID | `power_line=5` |

Export on NULLXES GPU servers → fill `model.onnx` + `sha256` in `pack.yaml`.  
Civil only — no weapon packs (ADR-004).

**Train:** [TRAIN.md](./TRAIN.md) — image PyTorch only, never `pip install torch`.
