#!/usr/bin/env bash
set -euo pipefail

# Astra GPU worker bootstrap.
# Safe default: validate prerequisites + create directories only.
# Optional model/repo setup requires explicit flags.
#
# Usage:
#   bash scripts/bootstrap_astra_gpu.sh
#   bash scripts/bootstrap_astra_gpu.sh --install-ltx
#   bash scripts/bootstrap_astra_gpu.sh --install-wan
#   bash scripts/bootstrap_astra_gpu.sh --install-ltx --install-wan
#
# This script does NOT:
# - register a GitHub Actions runner
# - request/store GitHub tokens
# - enable paid APIs
# - download model weights unless explicitly requested below

ROOT="${ASTRA_GPU_ROOT:-$HOME/astra-gpu}"
LTX_ROOT="${ASTRA_LTX_ROOT:-$ROOT/LTX-Video}"
WAN_ROOT="${ASTRA_WAN22_ROOT:-$ROOT/Wan2.2}"
VENV="${ASTRA_GPU_VENV:-$ROOT/venv}"
INSTALL_LTX=0
INSTALL_WAN=0

for arg in "$@"; do
  case "$arg" in
    --install-ltx) INSTALL_LTX=1 ;;
    --install-wan) INSTALL_WAN=1 ;;
    --help|-h)
      sed -n '1,45p' "$0"
      exit 0
      ;;
    *)
      echo "Unknown argument: $arg" >&2
      exit 2
      ;;
  esac
done

need() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "Missing required command: $1" >&2
    exit 1
  }
}

need git
need python3
need ffmpeg
need nvidia-smi

echo "== NVIDIA GPU =="
nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader

mkdir -p "$ROOT"
python3 -m venv "$VENV"
# shellcheck disable=SC1091
source "$VENV/bin/activate"
python -m pip install --upgrade pip wheel setuptools

if [[ "$INSTALL_LTX" == "1" ]]; then
  if [[ ! -d "$LTX_ROOT/.git" ]]; then
    git clone --depth 1 https://github.com/Lightricks/LTX-Video.git "$LTX_ROOT"
  fi
  if [[ -f "$LTX_ROOT/requirements.txt" ]]; then
    python -m pip install -r "$LTX_ROOT/requirements.txt"
  fi
  echo "LTX repository ready at: $LTX_ROOT"
  echo "Model weights are NOT auto-downloaded by Astra bootstrap."
fi

if [[ "$INSTALL_WAN" == "1" ]]; then
  if [[ ! -d "$WAN_ROOT/.git" ]]; then
    git clone --depth 1 https://github.com/Wan-Video/Wan2.2.git "$WAN_ROOT"
  fi
  if [[ -f "$WAN_ROOT/requirements.txt" ]]; then
    python -m pip install -r "$WAN_ROOT/requirements.txt"
  fi
  echo "Wan2.2 repository ready at: $WAN_ROOT"
  echo "Model checkpoints are NOT auto-downloaded by Astra bootstrap."
fi

cat <<EOF

Astra GPU bootstrap complete.

Suggested repository variables:
  ASTRA_LTX_ROOT=$LTX_ROOT
  ASTRA_WAN22_ROOT=$WAN_ROOT
  ASTRA_OSS_VIDEO_PROVIDER=auto

For LTX, also set ASTRA_LTX_CONFIG to an installed config path.
For Wan2.2, set ASTRA_WAN22_CKPT to the checkpoint directory.

Paid generation remains disabled unless ASTRA_ALLOW_PAID_CHARACTER_VIDEO=1
is explicitly set elsewhere.

To validate this machine from the Astra repository:
  source "$VENV/bin/activate"
  python gpu_worker_health.py

GitHub runner registration is intentionally separate because GitHub supplies
a short-lived registration token. When registering, include label:
  astra-gpu
EOF
