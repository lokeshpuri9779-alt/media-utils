#!/usr/bin/env bash
# Manual CPU-only SD1.5 benchmark. No Actions trigger, publishing, or secrets.
set -euo pipefail
cd "$(dirname "$0")/.."
export CUDA_VISIBLE_DEVICES=""
export HF_HUB_DISABLE_TELEMETRY=1
export TOKENIZERS_PARALLELISM=false
python -m venv .venv-meta-cpu
source .venv-meta-cpu/bin/activate
python -m pip install --upgrade pip
# CPU wheel source avoids installing GPU CUDA packages on Linux.
python -m pip install torch --index-url https://download.pytorch.org/whl/cpu
python -m pip install 'diffusers>=0.30,<0.38' 'transformers>=4.44,<5' 'accelerate>=0.30,<2' 'safetensors>=0.4,<1' 'Pillow>=10,<13'
python -m unittest discover -s tests -p 'test_meta_sd15_queue*.py' -v
python tools/meta_cpu_benchmark.py --profile quality --steps 25 --output artifacts/meta_sd15_first.png
