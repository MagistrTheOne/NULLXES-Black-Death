#!/usr/bin/env bash
# ATLAS-ALLOC only. No CERBER, no pictures, no pip torch.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"
cd "$ROOT_DIR"

export PYTHONUNBUFFERED=1
OUT="${ATLAS_OUT:-/workspace/atlas}"
CFG="06_autonomy/models/atlas/configs/alloc_v1.yaml"
PACK="06_autonomy/models/atlas"

echo "=== ATLAS-ALLOC RunPod ==="
echo "REPO=$ROOT_DIR"
echo "OUT=$OUT"

python - <<'PY'
import sys
try:
    import torch
except ImportError:
    print("BLOCKED: torch missing — use PyTorch CUDA image, do not pip install torch", file=sys.stderr)
    sys.exit(1)
print("torch", torch.__version__, "cuda", torch.cuda.is_available())
if not torch.cuda.is_available():
    print("BLOCKED: CUDA false", file=sys.stderr)
    sys.exit(1)
print("gpu", torch.cuda.get_device_name(0), "cap", torch.cuda.get_device_capability())
x = torch.zeros(1, device="cuda")
print("tensor", x.device)
PY

mkdir -p "$OUT"
pip install -q pyyaml numpy onnx

python "$PACK/scripts/train_alloc.py" --config "$CFG" --out "$OUT/alloc_v1.pth"
python "$PACK/scripts/export_alloc.py" --config "$CFG" --weights "$OUT/alloc_v1.pth" --out "$OUT/model.onnx"

if [[ ! -f "$OUT/model.onnx" ]]; then
  echo "BLOCKED: missing $OUT/model.onnx" >&2
  exit 1
fi

echo "=== SHA ==="
sha256sum "$OUT/model.onnx"
echo "CANDIDATE only until val match >= 0.90 and pack.yaml STABLE"
echo "copy $OUT/model.onnx home; do not git add *.onnx"
echo "=== DONE — STOP THE POD ==="
