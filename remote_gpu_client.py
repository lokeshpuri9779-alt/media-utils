from __future__ import annotations

"""Remote Astra GPU worker queued-job client."""

import os
import time
from pathlib import Path

import httpx


class RemoteGPUUnavailable(RuntimeError):
    pass


def _base_url() -> str:
    return (os.environ.get("ASTRA_GPU_WORKER_URL") or "").strip().rstrip("/")


def _token() -> str:
    return (os.environ.get("ASTRA_GPU_WORKER_TOKEN") or "").strip()


def _headers() -> dict:
    return {"Authorization":f"Bearer {_token()}"}


def remote_status(timeout: float = 8.0) -> dict:
    url=_base_url()
    token=_token()
    if not url or not token:
        return {"configured":False,"ready":False}
    try:
        r=httpx.get(url+"/health",headers=_headers(),timeout=timeout)
        if r.status_code!=200:
            return {"configured":True,"ready":False,"status_code":r.status_code}
        payload=r.json()
        return {"configured":True,"ready":bool(payload.get("ready")),"worker":payload}
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
    deadline=time.monotonic()+timeout_seconds
    try:
        with httpx.Client(timeout=30,follow_redirects=True) as client:
            submit=client.post(url+"/jobs",headers=_headers(),json=payload)
            if submit.status_code!=202:
                raise RemoteGPUUnavailable(
                    f"Remote GPU submit failed: HTTP {submit.status_code} {submit.text[:300]}"
                )
            job_id=str(submit.json().get("id") or "")
            if not job_id:
                raise RemoteGPUUnavailable("Remote GPU worker returned no job id.")

            while time.monotonic()<deadline:
                poll=client.get(url+f"/jobs/{job_id}",headers=_headers())
                if poll.status_code!=200:
                    raise RemoteGPUUnavailable(
                        f"Remote GPU poll failed: HTTP {poll.status_code} {poll.text[:300]}"
                    )
                status=poll.json()
                state=status.get("status")
                if state=="failed":
                    raise RemoteGPUUnavailable(
                        "Remote GPU render failed: "+str(status.get("error") or "unknown")
                    )
                if state=="succeeded":
                    video=client.get(url+f"/jobs/{job_id}/video",headers=_headers(),timeout=120)
                    if video.status_code!=200:
                        raise RemoteGPUUnavailable(
                            f"Remote GPU download failed: HTTP {video.status_code}"
                        )
                    ctype=str(video.headers.get("content-type") or "").lower()
                    if "video/" not in ctype and "octet-stream" not in ctype:
                        raise RemoteGPUUnavailable("Remote GPU worker returned non-video content.")
                    output_path.write_bytes(video.content)
                    if output_path.stat().st_size<=0:
                        raise RemoteGPUUnavailable("Remote GPU worker returned an empty video.")
                    return {
                        "provider":"remote-open-source-gpu",
                        "worker_provider":status.get("provider"),
                        "job_id":job_id,
                        "output_path":str(output_path),
                        "bytes":output_path.stat().st_size,
                        "paid_generation":False,
                    }
                time.sleep(5)
    except RemoteGPUUnavailable:
        raise
    except Exception as exc:
        raise RemoteGPUUnavailable(str(exc)) from exc

    raise RemoteGPUUnavailable("Remote GPU render timed out.")
