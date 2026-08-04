#!/usr/bin/env bash
# CERBER V2 — bare RunPod: prepare → train → export (no Docker)
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"
cd "$ROOT_DIR"

export CERBER_V2_ROOT="${CERBER_V2_ROOT:-/workspace/datasets/cerber_v2}"
PACK="06_autonomy/models/cerber_v2"
SCRIPTS="$PACK/scripts"

echo "=== CERBER V2 RunPod ==="
echo "REPO=$ROOT_DIR"
echo "CERBER_V2_ROOT=$CERBER_V2_ROOT"
echo "HF_TOKEN set: $([ -n "${HF_TOKEN:-}" ] && echo yes || echo no)"

mkdir -p "$CERBER_V2_ROOT"
pip install -q -r "$PACK/requirements.txt"

python "$SCRIPTS/prepare_data.py" --root "$CERBER_V2_ROOT" --full-seraphim --merge-local-uav
python "$SCRIPTS/train.py" --data "$CERBER_V2_ROOT/data.yaml"

BEST="runs/detect/cerber-detect/v2-pursuit/weights/best.pt"
if [[ ! -f "$BEST" ]]; then
  echo "BLOCKED: missing $BEST"
  exit 1
fi

python "$SCRIPTS/export_onnx.py" --weights "$BEST"

echo "=== DONE ==="
echo "ONNX: 06_autonomy/models/onnx/detector_alpha_v2b.onnx"
echo "CFG:  06_autonomy/models/configs/detector_alpha_v2b.yaml"
echo "Copy onnx+yaml home; smoke: python 06_autonomy/models/scripts/webcam_cerber_smoke.py"
