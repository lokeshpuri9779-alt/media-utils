#!/usr/bin/env bash
set -euo pipefail

echo "[Astra] Free GPU admission..."
python free_gpu_admission.py | tee /tmp/astra_gpu.json
python - <<'PY'
import json,sys
x=json.load(open("/tmp/astra_gpu.json"))
if not x.get("admitted"):
    raise SystemExit("Astra blocked: this runtime has less than 14 GB usable GPU memory.")
print("[Astra] GPU admitted:", x["gpus"])
PY

if [ ! -d /content/HunyuanVideo-1.5 ]; then
  git clone --depth 1 https://github.com/Tencent-Hunyuan/HunyuanVideo-1.5.git /content/HunyuanVideo-1.5
fi
cd /content/HunyuanVideo-1.5
python -m pip install -U pip
if [ -f requirements.txt ]; then pip install -r requirements.txt; fi

echo "[Astra] Hunyuan environment prepared."
echo "[Astra] Keep pilots private. Model/checkpoint download and generation follow only after GPU admission."
