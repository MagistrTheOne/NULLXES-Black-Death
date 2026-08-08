#!/usr/bin/env bash
# POSEIDON one-pack train+export on RunPod / farm (image torch — no pip torch).
set -euo pipefail

PACK="${1:?usage: runpod_pack.sh <pack_id>}"
ROOT="$(cd "$(dirname "$0")/../../../.." && pwd)"
cd "$ROOT"

POSEIDON_DATA_ROOT="${POSEIDON_DATA_ROOT:-/workspace/datasets/poseidon}"
CFG="06_autonomy/models/poseidon/configs/train_${PACK}.yaml"
DATA="${POSEIDON_DATA_ROOT}/${PACK}/data.yaml"

python - <<'PY'
import sys
try:
    import torch
except ImportError:
    print("BLOCKED: torch missing — use PyTorch CUDA image, do not pip install torch", file=sys.stderr)
    sys.exit(1)
print("torch", torch.__version__, "cuda", torch.cuda.is_available())
if torch.cuda.is_available():
    print("gpu", torch.cuda.get_device_name(0))
PY

if [[ ! -f "$CFG" ]]; then
  echo "BLOCKED: missing $CFG" >&2
  exit 1
fi
if [[ ! -f "$DATA" ]]; then
  echo "BLOCKED: missing $DATA — prepare YOLO tree under $POSEIDON_DATA_ROOT/$PACK/" >&2
  exit 1
fi

pip install -r 06_autonomy/models/poseidon/requirements.txt

python 06_autonomy/models/poseidon/scripts/train_pack.py \
  --train-config "$CFG" \
  --data "$DATA"

RUN="runs/detect/poseidon-${PACK}/weights/best.pt"
if [[ ! -f "$RUN" ]]; then
  # ultralytics may nest under project/name
  RUN=$(find runs -path "*poseidon-${PACK}*/weights/best.pt" | head -n1 || true)
fi
if [[ -z "${RUN}" || ! -f "$RUN" ]]; then
  echo "BLOCKED: best.pt not found for pack=$PACK" >&2
  exit 1
fi

python 06_autonomy/models/poseidon/scripts/export_pack.py --pack "$PACK" --weights "$RUN"
python 06_autonomy/models/poseidon/scripts/validate_registry.py
echo "POSEIDON pack=$PACK ready"
