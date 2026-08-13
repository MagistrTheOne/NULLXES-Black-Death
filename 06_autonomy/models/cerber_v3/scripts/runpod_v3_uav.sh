#!/usr/bin/env bash
# CERBER V3 UAV recovery: more Seraphim, 20 ep from v3-power/best.pt. No v2b overwrite. No ATLAS.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"
cd "$ROOT_DIR"

if [[ -f /workspace/.hf_env ]]; then
  # shellcheck disable=SC1091
  source /workspace/.hf_env
fi
export YOLO_AUTOINSTALL=false
export PYTHONUNBUFFERED=1
export CERBER_V3_ROOT="${CERBER_V3_ROOT:-/workspace/datasets/cerber_v3}"
V2="06_autonomy/models/cerber_v2"
V3="06_autonomy/models/cerber_v3"
BEST_IN="runs/detect/cerber-detect/v3-power/weights/best.pt"
BEST_OUT="runs/detect/cerber-detect/v3-uav/weights/best.pt"

echo "=== CERBER V3 UAV recovery ==="
echo "REPO=$ROOT_DIR ROOT=$CERBER_V3_ROOT"

if [[ ! -f "$BEST_IN" ]]; then
  echo "BLOCKED: missing $BEST_IN — run v3-power first" >&2
  exit 1
fi
if [[ ! -f "$CERBER_V3_ROOT/data.yaml" ]]; then
  echo "BLOCKED: missing $CERBER_V3_ROOT/data.yaml" >&2
  exit 1
fi

python - <<'PY'
import sys
try:
    import torch
except ImportError:
    print("BLOCKED: torch missing", file=sys.stderr)
    sys.exit(1)
print("torch", torch.__version__, "cuda", torch.cuda.is_available())
if not torch.cuda.is_available():
    print("BLOCKED: CUDA false", file=sys.stderr)
    sys.exit(1)
print("gpu", torch.cuda.get_device_name(0))
PY

# Drop old uav_* only (keep vd_* + power_line). Re-merge Seraphim at full test/ cap.
python - <<PY
from pathlib import Path
root = Path("$CERBER_V3_ROOT")
n = 0
for split in ("train", "val"):
    for p in list((root / "images" / split).glob("uav_*")):
        p.unlink()
        n += 1
    for p in list((root / "labels" / split).glob("uav_*")):
        p.unlink()
print(f"removed uav_* images={n}")
PY

MERGE=(
  python
  "06_autonomy/models/scripts/merge_uav_seraphim.py"
  --root "$CERBER_V3_ROOT"
  --skip-download
  --max-train "${SERAPHIM_MAX_TRAIN:-12000}"
)
if [[ -d "$CERBER_V3_ROOT/sources/seraphim_uav/train" && "${SERAPHIM_FULL:-0}" == "1" ]]; then
  MERGE+=(--full)
  echo "seraphim --full (train/ present)"
fi
"${MERGE[@]}"

python - <<PY
from pathlib import Path
root = Path("$CERBER_V3_ROOT")
for cache in (root / "labels" / "train.cache", root / "labels" / "val.cache"):
    if cache.is_file():
        cache.unlink()
        print(f"removed {cache}")
n_tr = len(list((root / "images" / "train").glob("*.*")))
n_va = len(list((root / "images" / "val").glob("*.*")))
n_uav_tr = len(list((root / "images" / "train").glob("uav_*")))
n_uav_va = len(list((root / "images" / "val").glob("uav_*")))
print(f"READY train={n_tr} val={n_va} uav_train={n_uav_tr} uav_val={n_uav_va}")
if n_uav_tr < 2000:
    raise SystemExit("BLOCKED: uav train too small")
PY

VRAM_GB="$(python -c "import torch; print(int(torch.cuda.get_device_properties(0).total_memory/1e9) if torch.cuda.is_available() else 0)")"
BATCH="${CERBER_BATCH:-}"
if [[ -z "$BATCH" ]]; then
  if [[ "${VRAM_GB:-0}" -ge 80 ]]; then BATCH=32; else BATCH=12; fi
fi
EPOCHS="${CERBER_EPOCHS:-20}"
echo "uav-ft batch=$BATCH epochs=$EPOCHS vram_gb=$VRAM_GB from=$BEST_IN"

python "$V2/scripts/train.py" \
  --train-config "$V3/configs/train_uav.yaml" \
  --data "$CERBER_V3_ROOT/data.yaml" \
  --weights "$BEST_IN" \
  --batch "$BATCH" \
  --epochs "$EPOCHS"

if [[ ! -f "$BEST_OUT" ]]; then
  echo "BLOCKED: missing $BEST_OUT" >&2
  exit 1
fi

python "$V2/scripts/export_onnx.py" --weights "$BEST_OUT" --train-config "$V3/configs/train_uav.yaml"

echo "=== UAV recovery DONE — copy detector_alpha_v3.onnx home; do not git add onnx ==="
echo "STOP THE POD after copy"
echo "STABLE only if uav mAP50 >= 0.926 and power_line > 0.25 and human/vehicle not collapsed"
