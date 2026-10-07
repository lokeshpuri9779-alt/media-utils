from __future__ import annotations

"""Free Agnes video backend for Astra.

Supports text-to-video plus Agnes image-to-video/keyframe continuity.
No paid fallback is used here.
"""

import base64
import mimetypes
import os
import time
from pathlib import Path

import httpx

from character_render_cache import RenderCache


BASE_URL="https://apihub.agnes-ai.com/v1"
POLL_URL="https://apihub.agnes-ai.com/agnesapi"
MODEL="agnes-video-v2.0"


class AgnesFreeVideoUnavailable(RuntimeError):
    pass


def _key() -> str:
    return (os.environ.get("AGNES_API_KEY") or "").strip()


def agnes_status() -> dict:
    return {
        "configured":bool(_key()),
        "ready":bool(_key()),
        "provider":"agnes-free-video",
        "cost_class":"free-api",
        "autonomous_allowed":True,
    }


def _frame_config(duration: float) -> tuple[int,int]:
    seconds=max(2.0,min(float(duration),5.0))
    fps=24
    frames=int(seconds*fps)+1
    frames=max(49,min(121,((frames-1)//8)*8+1))
    return frames,fps


def _resolve_refs(shot: dict) -> list[str]:
    out=[]
    for raw in (shot.get("reference_image_paths") or []):
        ref=str(raw).strip()
        if not ref:
            continue
        if ref.startswith(("http://","https://","data:")):
            out.append(ref)
            continue
        p=Path(ref)
        if not p.is_file():
            raise AgnesFreeVideoUnavailable(f"Agnes reference image is missing: {ref}")
        mime=mimetypes.guess_type(str(p))[0] or "image/png"
        out.append(f"data:{mime};base64,"+base64.b64encode(p.read_bytes()).decode("ascii"))
    return out


def generate_agnes_clip(
    shot: dict,
    output_path: str | Path,
    *,
    timeout_seconds: int = 1800,
    poll_interval: int = 30,
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

    refs=_resolve_refs(shot)
    mode="text-to-video"
    if len(refs)==1:
        payload["image"]=refs[0]
        payload["mode"]="ti2vid"
        mode="image-to-video"
    elif len(refs)>1:
        payload["extra_body"]={"image":refs[:2],"mode":"keyframes"}
        mode="keyframes"

    output_path=Path(output_path)
    cache=RenderCache({"endpoint":BASE_URL, "payload":payload}, key)
    cached=cache.completed(output_path)
    if cached is not None:
        return cached
    video_id=cache.pending_job()
    resumed=video_id is not None
    headers={"Authorization":f"Bearer {key}","Content-Type":"application/json"}
    started=time.monotonic()
    deadline=started+timeout_seconds

    try:
        with httpx.Client(timeout=90,follow_redirects=True) as client:
            if video_id is None:
                submit=client.post(f"{BASE_URL}/videos",headers=headers,json=payload)
                if submit.status_code!=200:
                    raise AgnesFreeVideoUnavailable(
                        f"Agnes submit failed: HTTP {submit.status_code} {submit.text[:300]}"
                    )
                body=submit.json()
                video_id=body.get("video_id") or body.get("task_id") or body.get("id")
                if not video_id:
                    raise AgnesFreeVideoUnavailable("Agnes returned no video id.")
                # Checkpoint immediately; a retry resumes this job instead of buying
                # another place in the free queue for an identical request.
                cache.submitted(str(video_id))

            final=None
            backoff=max(30,int(poll_interval))
            while time.monotonic()<deadline:
                poll=client.get(POLL_URL,params={"video_id":video_id},headers=headers,timeout=30)
                if poll.status_code==429:
                    retry_after=poll.headers.get("Retry-After")
                    try:
                        delay=max(backoff,int(float(retry_after))) if retry_after else backoff
                    except (TypeError,ValueError):
                        delay=backoff
                    remaining=deadline-time.monotonic()
                    if delay>=remaining:
                        raise AgnesFreeVideoUnavailable(
                            f"Agnes requests a {delay}s cooldown; job checkpoint saved for a later run."
                        )
                    time.sleep(delay)
                    backoff=min(backoff*2,180)
                    continue
                if poll.status_code!=200:
                    raise AgnesFreeVideoUnavailable(
                        f"Agnes poll failed: HTTP {poll.status_code} {poll.text[:300]}"
                    )

                backoff=max(30,int(poll_interval))
                state=poll.json()
                status=str(state.get("status") or "").lower()
                if status=="failed":
                    cache.failed()
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

    report = {
        "provider":"agnes-free-video",
        "video_id":str(video_id),
        "output_path":str(output_path),
        "bytes":output_path.stat().st_size,
        "paid_generation":False,
        "width":768,
        "height":1152,
        "num_frames":frames,
        "frame_rate":fps,
        "generation_mode":mode,
        "reference_images":len(refs),
        "cache_hit":False,
        "resumed_job":resumed,
        "elapsed_seconds":round(time.monotonic()-started, 3),
    }
    cache.finish(output_path, report)
    return report


# Probe marker: Agnes free backend active.
