from __future__ import annotations

"""Real character-video generation backend for Astra.

Default provider: Replicate official wan-video/wan-2.6-t2v.
Paid generation is intentionally double-gated:
- REPLICATE_API_TOKEN must exist
- ASTRA_ALLOW_PAID_CHARACTER_VIDEO must be explicitly truthy

Astra must never spend merely because a token exists.
"""

import json
import os
import time
from pathlib import Path

import httpx

from video_provider_policy import capability, autonomous_provider_allowed
from agnes_free_video import (
    AgnesFreeVideoUnavailable,
    agnes_status,
    generate_agnes_clip,
)

from open_source_video_engine import (
    OpenSourceVideoUnavailable,
    generate_open_source_clip,
    provider_status as open_source_provider_status,
)
from remote_gpu_client import (
    RemoteGPUUnavailable,
    generate_remote_clip,
    remote_status,
)
from hf_zerogpu_adapter import (
    ZeroGPUUnavailable,
    generate_zerogpu_clip,
    zerogpu_status,
)

MODEL = "wan-video/wan-2.6-t2v"
CREATE_URL = "https://api.replicate.com/v1/models/wan-video/wan-2.6-t2v/predictions"
MAX_VIDEO_BYTES = 80_000_000


class CharacterVideoUnavailable(RuntimeError):
    pass


def paid_generation_enabled() -> bool:
    return str(os.environ.get("ASTRA_ALLOW_PAID_CHARACTER_VIDEO") or "").strip().lower() in {
        "1", "true", "yes", "on"
    }


def provider_status() -> dict:
    agnes=agnes_status()
    selected="agnes-free-video" if agnes.get("ready") else None
    return {
        "mode": "agnes-free-only",
        "selected": selected,
        "ready": bool(agnes.get("ready")),
        "agnes_free_video": agnes,
        "selected_capability": capability(selected),
        "paid_fallback": {
            "provider": "replicate",
            "model": MODEL,
            "token_configured": bool((os.environ.get("REPLICATE_API_TOKEN") or "").strip()),
            "paid_generation_enabled": paid_generation_enabled(),
            "ready": False,
        },
    }


def _token() -> str:
    token = (os.environ.get("REPLICATE_API_TOKEN") or "").strip()
    if not token:
        raise CharacterVideoUnavailable("REPLICATE_API_TOKEN is not configured.")
    if not paid_generation_enabled():
        raise CharacterVideoUnavailable(
            "Paid character-video generation is disabled. "
            "Set ASTRA_ALLOW_PAID_CHARACTER_VIDEO=1 only after explicit spend approval."
        )
    return token


def _prediction_output_url(payload: dict) -> str:
    out = payload.get("output")
    if isinstance(out, str) and out.startswith("https://"):
        return out
    if isinstance(out, list):
        for item in out:
            if isinstance(item, str) and item.startswith("https://"):
                return item
    return ""


def _generate_paid_character_clip(shot: dict, output_path: str | Path, timeout_seconds: int = 720) -> dict:
    token = _token()
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    target = shot.get("target_seconds") or [1.8, 3.2]
    if isinstance(target, (list, tuple)) and target:
        requested = float(max(target))
    else:
        requested = float(target or 3.0)
    # WAN 2.6 supports generated-video durations in seconds; use a stable 5s
    # single shot then Astra trims it during composition.
    generation_duration = 5 if requested <= 5 else 10

    payload = {
        "input": {
            "size": str(os.environ.get("ASTRA_CHARACTER_VIDEO_SIZE") or "720*1280"),
            "prompt": str(shot.get("prompt") or ""),
            "duration": generation_duration,
            "multi_shots": False,
            "negative_prompt": str(shot.get("negative") or ""),
            "enable_prompt_expansion": True,
        }
    }
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Prefer": "wait=60",
    }

    with httpx.Client(timeout=75, follow_redirects=True) as client:
        response = client.post(CREATE_URL, headers=headers, json=payload)
        response.raise_for_status()
        prediction = response.json()

        deadline = time.monotonic() + timeout_seconds
        while prediction.get("status") in {"starting", "processing"}:
            if time.monotonic() >= deadline:
                cancel = ((prediction.get("urls") or {}).get("cancel") or "")
                if cancel:
                    try:
                        client.post(cancel, headers={"Authorization": f"Bearer {token}"})
                    except Exception:
                        pass
                raise TimeoutError("Character-video generation exceeded Astra timeout.")
            get_url = ((prediction.get("urls") or {}).get("get") or "")
            if not get_url:
                raise RuntimeError("Replicate prediction did not provide a status URL.")
            time.sleep(4)
            poll = client.get(get_url, headers={"Authorization": f"Bearer {token}"})
            poll.raise_for_status()
            prediction = poll.json()

        if prediction.get("status") != "succeeded":
            raise RuntimeError(
                "Character-video provider failed: "
                + str(prediction.get("error") or prediction.get("status") or "unknown")
            )

        video_url = _prediction_output_url(prediction)
        if not video_url:
            raise RuntimeError("Character-video provider returned no downloadable video.")

        with client.stream("GET", video_url) as download:
            download.raise_for_status()
            ctype = str(download.headers.get("content-type") or "").lower()
            if "video/" not in ctype and "octet-stream" not in ctype:
                raise RuntimeError("Character-video provider returned a non-video payload.")
            total = 0
            with output_path.open("wb") as handle:
                for block in download.iter_bytes(1024 * 1024):
                    total += len(block)
                    if total > MAX_VIDEO_BYTES:
                        raise RuntimeError("Generated character clip exceeded Astra size limit.")
                    handle.write(block)

    if not output_path.is_file() or output_path.stat().st_size <= 0:
        raise RuntimeError("Generated character clip is empty.")

    return {
        "provider": "replicate",
        "model": MODEL,
        "prediction_id": prediction.get("id"),
        "output_path": str(output_path),
        "bytes": output_path.stat().st_size,
        "generation_duration": generation_duration,
        "requested_target_seconds": requested,
        "paid_generation": True,
    }


def generate_character_clip(shot: dict, output_path: str | Path, timeout_seconds: int = 720) -> dict:
    """Generate through Agnes only.

    Legacy GPU/ZeroGPU/paid providers remain in source for rollback/history, but
    this active path intentionally does not call them.
    """
    try:
        return generate_agnes_clip(
            shot,
            output_path,
            timeout_seconds=max(timeout_seconds, 1800),
        )
    except AgnesFreeVideoUnavailable as exc:
        raise CharacterVideoUnavailable(
            "Agnes free video backend is unavailable: " + str(exc)
        ) from exc


def generate_storyboard(storyboard: list[dict], root: str | Path) -> tuple[list[Path], list[dict]]:
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    clips, reports = [], []
    for i, shot in enumerate(storyboard):
        path = root / f"character_scene_{i+1:02d}.mp4"
        report = generate_character_clip(shot, path)
        clips.append(path)
        reports.append(report)
    return clips, reports
