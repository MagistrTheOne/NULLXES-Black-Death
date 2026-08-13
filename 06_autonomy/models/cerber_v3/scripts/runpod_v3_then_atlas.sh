#!/usr/bin/env bash
# CERBER V3 then ATLAS-ALLOC on the same RunPod GPU. No Docker. Do not pip torch.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"
cd "$ROOT_DIR"

if [[ -f /workspace/.hf_env ]]; then
  # shellcheck disable=SC1091
  source /workspace/.hf_env
fi
export YOLO_AUTOINSTALL=false
if [[ -d "$ROOT_DIR/datasets/VisDrone/images/train" ]]; then
  export VISDRONE_DIR="${VISDRONE_DIR:-$ROOT_DIR/datasets/VisDrone}"
else
  export VISDRONE_DIR="${VISDRONE_DIR:-/workspace/datasets/VisDrone}"
fi
export CERBER_V3_ROOT="${CERBER_V3_ROOT:-/workspace/datasets/cerber_v3}"
V2="06_autonomy/models/cerber_v2"
V3="06_autonomy/models/cerber_v3"
ATLAS="06_autonomy/models/atlas"

echo "=== CERBER V3 + ATLAS-ALLOC ==="
echo "REPO=$ROOT_DIR ROOT=$CERBER_V3_ROOT"
echo "VISDRONE_DIR=$VISDRONE_DIR"
echo "HF_TOKEN set: $([ -n "${HF_TOKEN:-}" ] && echo yes || echo no)"

python - <<'PY'
import sys
try:
    import torch
except ImportError:
    print("BLOCKED: torch missing — use PyTorch CUDA image", file=sys.stderr)
    sys.exit(1)
print("torch", torch.__version__, "cuda", torch.cuda.is_available())
if torch.cuda.is_available():
    print("gpu", torch.cuda.get_device_name(0))
PY

pip install -q -r "$V2/requirements.txt"
pip install -q 'pillow>=10,<12'
mkdir -p "$CERBER_V3_ROOT"

python "$V2/scripts/prepare_data.py" --root "$CERBER_V3_ROOT" --full-seraphim --merge-local-uav
python "$V3/scripts/fetch_powerline.py" --root "$CERBER_V3_ROOT"

python "$V2/scripts/train.py" \
  --train-config "$V3/configs/train.yaml" \
  --data "$CERBER_V3_ROOT/data.yaml"

BEST="runs/detect/cerber-detect/v3-power/weights/best.pt"
if [[ ! -f "$BEST" ]]; then
  echo "BLOCKED: missing $BEST" >&2
  exit 1
fi

python "$V2/scripts/export_onnx.py" --weights "$BEST" --train-config "$V3/configs/train.yaml"

echo "=== ATLAS-ALLOC (same GPU) ==="
bash "$ATLAS/scripts/runpod_alloc.sh"

echo "=== DONE — copy home, do not git add onnx ==="
echo "CERBER  06_autonomy/models/onnx/detector_alpha_v3.onnx"
echo "ATLAS   ${ATLAS_OUT:-/workspace/atlas}/model.onnx"
echo "STOP THE POD"
