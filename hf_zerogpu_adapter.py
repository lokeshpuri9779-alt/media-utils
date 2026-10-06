from __future__ import annotations

"""Hugging Face ZeroGPU adapter for Astra.

This backend is strictly opportunistic/free:
- requires an explicitly configured Space
- does not purchase credits
- fails closed when the Space is unavailable or quota is exhausted
"""

import os
import shutil
from pathlib import Path

from gradio_client import Client, handle_file


class ZeroGPUUnavailable(RuntimeError):
    pass


def _space() -> str:
    return (os.environ.get("ASTRA_HF_ZEROGPU_SPACE") or "").strip()


def _token() -> str | None:
    return (os.environ.get("HF_TOKEN") or "").strip() or None


def zerogpu_status() -> dict:
    space=_space()
    if not space:
        return {"configured":False,"ready":False}
    return {
        "configured":True,
        "ready":True,
        "space":space,
        "cost_class":"free-quota",
        "autonomous_allowed":True,
    }


def generate_zerogpu_clip(shot: dict, output_path: str | Path) -> dict:
    space=_space()
    if not space:
        raise ZeroGPUUnavailable("ZeroGPU Space is not configured.")

    output_path=Path(output_path)
    output_path.parent.mkdir(parents=True,exist_ok=True)

    try:
        client=Client(space,hf_token=_token(),verbose=False)
        result=client.predict(
            prompt=str(shot.get("prompt") or ""),
            negative=str(shot.get("negative") or ""),
            duration=float(shot.get("target_seconds") or 3.0),
            api_name="/render",
        )
    except Exception as exc:
        raise ZeroGPUUnavailable(f"ZeroGPU render unavailable: {exc}") from exc

    candidate=None
    if isinstance(result,str):
        candidate=result
    elif isinstance(result,(list,tuple)) and result:
        candidate=result[0]
    elif isinstance(result,dict):
        candidate=result.get("path") or result.get("video") or result.get("name")

    if not candidate:
        raise ZeroGPUUnavailable("ZeroGPU Space returned no video.")

    src=Path(str(candidate))
    if not src.is_file():
        raise ZeroGPUUnavailable("ZeroGPU result file is unavailable.")

    shutil.copyfile(src,output_path)
    if output_path.stat().st_size<=0:
        raise ZeroGPUUnavailable("ZeroGPU returned an empty video.")

    return {
        "provider":"hf-zerogpu",
        "space":space,
        "output_path":str(output_path),
        "bytes":output_path.stat().st_size,
        "paid_generation":False,
    }
