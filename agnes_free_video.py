from __future__ import annotations

"""Agnes free video backend for Astra.

Protocol derived from uglylee/free-video-generator (MIT):
https://github.com/uglylee/free-video-generator

This adapter intentionally implements only Astra's needs:
- text-to-video
- 9:16 output
- polling
- MP4 download
It requires AGNES_API_KEY and never falls through to a paid provider.
"""

import os
import time
from pathlib import Path

import httpx


BASE_URL="https://apihub.agnes-ai.com/v1"
POLL_URL="https://apihub.agnes-ai.com/agnesapi"
MODEL="agnes-video-v2.0"


class AgnesFreeVideoUnavailable(RuntimeError):
    pass


def _key() -> str:
    return (os.environ.get("AGNES_API_KEY") or "").strip()


def agnes_status() -> dict:
    return {
        "configured": bool(_key()),
        "ready": bool(_key()),
        "provider": "agnes-free-video",
        "cost_class": "free-api",
        "autonomous_allowed": True,
    }


def _frame_config(duration: float) -> tuple[int,int]:
    # Keep the free job compact and inside Agnes's 720p frame limit.
    seconds=max(2.0,min(float(duration),5.0))
    fps=24
    frames=int(seconds*fps)+1
    # Agnes expects frame counts on an 8n+1 cadence.
    frames=max(49,min(121,((frames-1)//8)*8+1))
    return frames,fps


def generate_agnes_clip(
    shot: dict,
    output_path: str | Path,
    *,
    timeout_seconds: int = 1800,
    poll_interval: int = 20,
) -> dict:
    key=_key()
    if not key:
        raise AgnesFreeVideoUnavailable("AGNES_API_KEY is not configured.")

    prompt=str(shot.get("prompt") or "").strip()
    if not prompt:
        raise AgnesFreeVideoUnavailable("Agnes prompt is empty.")

    target=shot.get("target_seconds") or 4.0
    if isinstance(target,(list,tuple)):
        target=sum(float(x) for x in target)/len(target)
    frames,fps=_frame_config(float(target))

    payload={
        "model":MODEL,
        "prompt":prompt,
        "width":768,
        "height":1152,
        "num_frames":frames,
        "frame_rate":fps,
    }
    negative=str(shot.get("negative") or "").strip()
    if negative:
        payload["negative_prompt"]=negative

    headers={"Authorization":f"Bearer {key}","Content-Type":"application/json"}
    deadline=time.monotonic()+timeout_seconds
    try:
        with httpx.Client(timeout=90,follow_redirects=True) as client:
            submit=client.post(f"{BASE_URL}/videos",headers=headers,json=payload)
            if submit.status_code!=200:
                raise AgnesFreeVideoUnavailable(
                    f"Agnes submit failed: HTTP {submit.status_code} {submit.text[:300]}"
                )
            body=submit.json()
            video_id=body.get("video_id") or body.get("task_id") or body.get("id")
            if not video_id:
                raise AgnesFreeVideoUnavailable("Agnes returned no video id.")

            final=None
            while time.monotonic()<deadline:
                poll=client.get(POLL_URL,params={"video_id":video_id},headers=headers,timeout=30)
                if poll.status_code!=200:
                    raise AgnesFreeVideoUnavailable(
                        f"Agnes poll failed: HTTP {poll.status_code} {poll.text[:300]}"
                    )
                state=poll.json()
                status=str(state.get("status") or "").lower()
                if status=="failed":
                    raise AgnesFreeVideoUnavailable(
                        "Agnes render failed: "+str(state.get("error") or "unknown")
                    )
                if status=="completed":
                    final=state
                    break
                time.sleep(poll_interval)

            if final is None:
                raise AgnesFreeVideoUnavailable("Agnes render timed out.")

            url=(
                final.get("remixed_from_video_id")
                or final.get("video_url")
                or final.get("url")
                or ((final.get("data") or {}).get("video_url") if isinstance(final.get("data"),dict) else None)
                or ((final.get("data") or {}).get("url") if isinstance(final.get("data"),dict) else None)
            )
            if not url or not str(url).startswith(("http://","https://")):
                raise AgnesFreeVideoUnavailable("Agnes completed without a downloadable video URL.")

            video=client.get(str(url),timeout=120)
            video.raise_for_status()
    except AgnesFreeVideoUnavailable:
        raise
    except Exception as exc:
        raise AgnesFreeVideoUnavailable(str(exc)) from exc

    output_path=Path(output_path)
    output_path.parent.mkdir(parents=True,exist_ok=True)
    output_path.write_bytes(video.content)
    if output_path.stat().st_size<=0:
        raise AgnesFreeVideoUnavailable("Agnes returned an empty video.")

    return {
        "provider":"agnes-free-video",
        "video_id":str(video_id),
        "output_path":str(output_path),
        "bytes":output_path.stat().st_size,
        "paid_generation":False,
        "width":768,
        "height":1152,
        "num_frames":frames,
        "frame_rate":fps,
    }
