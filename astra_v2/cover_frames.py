"""No-cost story-frame covers for eligible ASTRA long-form uploads."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path


def extract_long_cover(video):
    """Select a real frame near the opening hook; never alter the video."""
    video = Path(video)
    if not video.is_file():
        raise ValueError("Missing long-form video")
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "json", str(video)],
        capture_output=True, text=True, timeout=30, check=True,
    )
    duration = float(json.loads(probe.stdout)["format"]["duration"])
    if duration <= 0:
        raise ValueError("Invalid video duration")
    timestamp = min(max(1.0, duration * 0.03), 15.0, duration / 2)
    destination = video.with_name(video.stem + "_cover_wide.jpg")
    subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
         "-ss", f"{timestamp:.3f}", "-i", str(video),
         "-frames:v", "1", "-vf",
         "scale=1280:720:force_original_aspect_ratio=increase,crop=1280:720",
         "-q:v", "3", str(destination)],
        capture_output=True, timeout=60, check=True,
    )
    if not destination.is_file() or not 0 < destination.stat().st_size <= 2 * 1024 * 1024:
        raise RuntimeError("Invalid long-form cover")
    return destination
