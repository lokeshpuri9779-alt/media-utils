from __future__ import annotations

"""Open-source-first character/video generation router for Astra.

Priority:
1. Local LTX-Video / LTX-2 compatible worker
2. Local Wan2.2 TI2V-5B worker
3. Paid remote provider only when explicitly authorized elsewhere

The adapters assume the model repository + weights are installed on a GPU
worker. They intentionally do not auto-download multi-GB weights at runtime.
"""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


class OpenSourceVideoUnavailable(RuntimeError):
    pass


def _truthy(name: str) -> bool:
    return str(os.environ.get(name) or "").strip().lower() in {"1","true","yes","on"}


def gpu_available() -> bool:
    exe=shutil.which("nvidia-smi")
    if not exe:
        return False
    try:
        r=subprocess.run([exe,"--query-gpu=name","--format=csv,noheader"],
                         capture_output=True,text=True,timeout=8)
        return r.returncode==0 and bool(r.stdout.strip())
    except Exception:
        return False


def ltx_status() -> dict:
    root=Path(os.environ.get("ASTRA_LTX_ROOT") or "")
    cfg=os.environ.get("ASTRA_LTX_CONFIG") or "configs/ltxv-2b-0.9.8-distilled.yaml"
    ready=bool(root and root.is_dir() and (root/"inference.py").is_file() and (root/cfg).is_file() and gpu_available())
    return {
        "provider":"ltx-local",
        "root":str(root) if str(root) else "",
        "config":cfg,
        "gpu_available":gpu_available(),
        "ready":ready,
        "paid_generation":False,
    }


def wan_status() -> dict:
    root=Path(os.environ.get("ASTRA_WAN22_ROOT") or "")
    ckpt=Path(os.environ.get("ASTRA_WAN22_CKPT") or "")
    ready=bool(root and root.is_dir() and (root/"generate.py").is_file()
               and ckpt and ckpt.is_dir() and gpu_available())
    return {
        "provider":"wan2.2-local",
        "root":str(root) if str(root) else "",
        "checkpoint":str(ckpt) if str(ckpt) else "",
        "gpu_available":gpu_available(),
        "ready":ready,
        "paid_generation":False,
    }


def provider_status() -> dict:
    ltx=ltx_status()
    wan=wan_status()
    preferred=(os.environ.get("ASTRA_OSS_VIDEO_PROVIDER") or "auto").strip().lower()
    if preferred=="ltx":
        selected="ltx-local" if ltx["ready"] else None
    elif preferred in {"wan","wan2.2","wan22"}:
        selected="wan2.2-local" if wan["ready"] else None
    else:
        selected="ltx-local" if ltx["ready"] else ("wan2.2-local" if wan["ready"] else None)
    return {
        "mode":"open-source-first",
        "preferred":preferred,
        "selected":selected,
        "ready":bool(selected),
        "backends":{"ltx":ltx,"wan2.2":wan},
    }


def _requested_frames(shot: dict, fps: int = 24) -> int:
    target=shot.get("target_seconds") or [1.8,3.2]
    if isinstance(target,(list,tuple)):
        sec=float(max(target))
    else:
        sec=float(target or 3.0)
    # LTX expects 8n+1 frames; keep character shots short.
    raw=max(25,min(121,int(round(sec*fps))))
    return max(25,((raw-1)//8)*8+1)


def generate_ltx(shot: dict, output: Path) -> dict:
    status=ltx_status()
    if not status["ready"]:
        raise OpenSourceVideoUnavailable("Local LTX backend is not ready.")
    root=Path(status["root"])
    output.parent.mkdir(parents=True,exist_ok=True)
    frames=_requested_frames(shot)
    seed=abs(hash(str(shot.get("prompt") or ""))) % 2_147_483_647
    cmd=[
        sys.executable,"inference.py",
        "--prompt",str(shot.get("prompt") or ""),
        "--height","1216","--width","704",
        "--num_frames",str(frames),
        "--seed",str(seed),
        "--pipeline_config",status["config"],
        "--output_path",str(output.resolve()),
    ]
    subprocess.run(cmd,cwd=root,check=True,timeout=1800)
    if not output.is_file() or output.stat().st_size<=0:
        raise RuntimeError("LTX completed without producing a video.")
    return {
        "provider":"ltx-local",
        "model_config":status["config"],
        "output_path":str(output),
        "frames":frames,
        "paid_generation":False,
    }


def generate_wan22(shot: dict, output: Path) -> dict:
    status=wan_status()
    if not status["ready"]:
        raise OpenSourceVideoUnavailable("Local Wan2.2 backend is not ready.")
    root=Path(status["root"])
    ckpt=Path(status["checkpoint"])
    output.parent.mkdir(parents=True,exist_ok=True)
    # Wan2.2's official TI2V-5B path supports 704x1280 on >=24 GB VRAM.
    cmd=[
        sys.executable,"generate.py",
        "--task","ti2v-5B",
        "--size","704*1280",
        "--ckpt_dir",str(ckpt),
        "--offload_model","True",
        "--convert_model_dtype",
        "--t5_cpu",
        "--prompt",str(shot.get("prompt") or ""),
        "--save_file",str(output.resolve()),
    ]
    subprocess.run(cmd,cwd=root,check=True,timeout=2400)
    if not output.is_file() or output.stat().st_size<=0:
        raise RuntimeError("Wan2.2 completed without producing a video.")
    return {
        "provider":"wan2.2-local",
        "task":"ti2v-5B",
        "output_path":str(output),
        "paid_generation":False,
    }


def generate_open_source_clip(shot: dict, output: str | Path) -> dict:
    output=Path(output)
    status=provider_status()
    selected=status.get("selected")
    if selected=="ltx-local":
        return generate_ltx(shot,output)
    if selected=="wan2.2-local":
        return generate_wan22(shot,output)
    raise OpenSourceVideoUnavailable(
        "No local open-source video backend is ready. Configure a GPU worker with "
        "ASTRA_LTX_ROOT or ASTRA_WAN22_ROOT/ASTRA_WAN22_CKPT."
    )
