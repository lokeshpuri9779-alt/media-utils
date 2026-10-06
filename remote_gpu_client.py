from __future__ import annotations

"""Remote Astra GPU worker client.

Allows the GitHub-hosted controller to delegate an individual open-source video
shot to a separately attached GPU machine. The worker remains self-hosted and
paid-provider fallback stays disabled unless explicitly authorized elsewhere.
"""

import os
from pathlib import Path

import httpx


class RemoteGPUUnavailable(RuntimeError):
    pass


def _base_url() -> str:
    return (os.environ.get("ASTRA_GPU_WORKER_URL") or "").strip().rstrip("/")


def _token() -> str:
    return (os.environ.get("ASTRA_GPU_WORKER_TOKEN") or "").strip()


def remote_status(timeout: float = 8.0) -> dict:
    url=_base_url()
    token=_token()
    if not url or not token:
        return {"configured":False,"ready":False}
    try:
        r=httpx.get(
            url+"/health",
            headers={"Authorization":f"Bearer {token}"},
            timeout=timeout,
        )
        if r.status_code!=200:
            return {"configured":True,"ready":False,"status_code":r.status_code}
        payload=r.json()
        return {
            "configured":True,
            "ready":bool(payload.get("ready")),
            "worker":payload,
        }
    except Exception as exc:
        return {"configured":True,"ready":False,"error":str(exc)}


def generate_remote_clip(shot: dict, output_path: str | Path, timeout_seconds: int = 1800) -> dict:
    url=_base_url()
    token=_token()
    if not url or not token:
        raise RemoteGPUUnavailable("Remote GPU worker is not configured.")

    output_path=Path(output_path)
    output_path.parent.mkdir(parents=True,exist_ok=True)
    payload={
        "prompt":str(shot.get("prompt") or ""),
        "negative":str(shot.get("negative") or ""),
        "target_seconds":shot.get("target_seconds") or [1.8,3.2],
        "variant":str(shot.get("variant") or ""),
    }
    with httpx.Client(timeout=timeout_seconds,follow_redirects=True) as client:
        r=client.post(
            url+"/render",
            headers={"Authorization":f"Bearer {token}"},
            json=payload,
        )
        if r.status_code!=200:
            raise RemoteGPUUnavailable(
                f"Remote GPU render failed: HTTP {r.status_code} {r.text[:300]}"
            )
        ctype=str(r.headers.get("content-type") or "").lower()
        if "video/" not in ctype and "octet-stream" not in ctype:
            raise RemoteGPUUnavailable("Remote GPU worker returned non-video content.")
        output_path.write_bytes(r.content)

    if not output_path.is_file() or output_path.stat().st_size<=0:
        raise RemoteGPUUnavailable("Remote GPU worker returned an empty video.")

    return {
        "provider":"remote-open-source-gpu",
        "output_path":str(output_path),
        "bytes":output_path.stat().st_size,
        "paid_generation":False,
    }
