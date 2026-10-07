"""Admission check for opportunistic free CUDA notebook sessions."""
from __future__ import annotations
import json, subprocess

MIN_VRAM_GB = 14.0

def cuda_capacity() -> dict:
    try:
        out=subprocess.check_output(
            ["nvidia-smi","--query-gpu=name,memory.total","--format=csv,noheader,nounits"],
            text=True, timeout=10
        ).strip().splitlines()
        rows=[]
        for line in out:
            name,mem=[x.strip() for x in line.rsplit(",",1)]
            rows.append({"name":name,"vram_gb":round(float(mem)/1024,2)})
        best=max((r["vram_gb"] for r in rows),default=0)
        return {"gpus":rows,"best_vram_gb":best,"admitted":best>=MIN_VRAM_GB,
                "minimum_vram_gb":MIN_VRAM_GB}
    except Exception as exc:
        return {"gpus":[],"best_vram_gb":0,"admitted":False,
                "minimum_vram_gb":MIN_VRAM_GB,"reason":type(exc).__name__}

if __name__=="__main__":
    print(json.dumps(cuda_capacity(),indent=2))
