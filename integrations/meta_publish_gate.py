"""Offline pre-publish gate for externally generated video clips.

This module does not upload anything or bypass Meta API limitations.
"""
from __future__ import annotations
import argparse
import json
import subprocess
from pathlib import Path

def ffprobe(path: Path) -> dict:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)],
        check=True, capture_output=True, text=True, timeout=30,
    )
    return json.loads(result.stdout)

def validate(path: Path, *, require_audio: bool = True, min_duration: float = 10.0) -> dict:
    errors = []
    if not path.is_file() or path.stat().st_size == 0:
        return {"ready": False, "errors": ["Video missing or empty"]}
    try:
        data = ffprobe(path)
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired, json.JSONDecodeError) as exc:
        return {"ready": False, "errors": [f"Probe failed: {type(exc).__name__}"]}
    streams = data.get("streams", [])
    videos = [s for s in streams if s.get("codec_type") == "video"]
    audios = [s for s in streams if s.get("codec_type") == "audio"]
    if len(videos) != 1:
        errors.append("Exactly one video stream required")
    else:
        v = videos[0]
        if int(v.get("width") or 0) != 1080 or int(v.get("height") or 0) != 1920:
            errors.append("Video must be 1080x1920 portrait")
        if v.get("codec_name") != "h264":
            errors.append("H.264 video required")
    if require_audio and not audios:
        errors.append("Audio track missing")
    try:
        duration = float(data.get("format", {}).get("duration", 0))
    except (TypeError, ValueError):
        duration = 0
    if duration < min_duration:
        errors.append(f"Video shorter than {min_duration} seconds")
    return {"ready": not errors, "errors": errors, "duration_seconds": duration, "audio_present": bool(audios)}

def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("video", type=Path)
    p.add_argument("--allow-silent", action="store_true")
    p.add_argument("--min-duration", type=float, default=10)
    args = p.parse_args()
    result = validate(args.video, require_audio=not args.allow_silent, min_duration=args.min_duration)
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["ready"] else 1)

if __name__ == "__main__":
    main()
