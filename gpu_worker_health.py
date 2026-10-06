from __future__ import annotations

"""GPU worker contract for Astra open-source video generation."""

import json
import os
import shutil
import subprocess
from pathlib import Path

from open_source_video_engine import provider_status


def gpu_info() -> dict:
    exe=shutil.which("nvidia-smi")
    if not exe:
        return {"available":False,"reason":"nvidia-smi not found"}
    try:
        q=[
            exe,
            "--query-gpu=name,memory.total,driver_version",
            "--format=csv,noheader,nounits",
        ]
        r=subprocess.run(q,capture_output=True,text=True,timeout=10)
        if r.returncode!=0:
            return {"available":False,"reason":r.stderr.strip() or "nvidia-smi failed"}
        rows=[]
        for line in r.stdout.splitlines():
            parts=[x.strip() for x in line.split(",")]
            if len(parts)>=3:
                rows.append({
                    "name":parts[0],
                    "memory_mb":int(float(parts[1])),
                    "driver":parts[2],
                })
        return {"available":bool(rows),"gpus":rows}
    except Exception as exc:
        return {"available":False,"reason":str(exc)}


def worker_health() -> dict:
    gpu=gpu_info()
    providers=provider_status()
    min_vram=min((g.get("memory_mb",0) for g in gpu.get("gpus",[])),default=0)
    return {
        "gpu":gpu,
        "providers":providers,
        "ltx_candidate":bool(gpu.get("available") and min_vram>=8000),
        "wan22_ti2v5b_candidate":bool(gpu.get("available") and min_vram>=24000),
        "paid_fallback_required":not providers.get("ready"),
    }


def assert_ready() -> dict:
    health=worker_health()
    if not health["gpu"].get("available"):
        raise SystemExit("GPU worker not ready: NVIDIA GPU not detected.")
    if not health["providers"].get("ready"):
        raise SystemExit(
            "GPU detected, but no open-source backend is configured. "
            "Set ASTRA_LTX_ROOT or ASTRA_WAN22_ROOT/ASTRA_WAN22_CKPT."
        )
    return health


if __name__=="__main__":
    print(json.dumps(worker_health(),indent=2))
