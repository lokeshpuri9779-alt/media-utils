"""No-cost story-frame covers for eligible ASTRA long-form uploads.

Choose an actual sharp, well-exposed frame from the opening portion of the
video rather than assuming the first sampled frame is suitable.
"""
from __future__ import annotations

import io
import json
import subprocess
from pathlib import Path


def _frame_score(jpeg):
    """Simple deterministic clarity/exposure heuristic, no paid vision API."""
    from PIL import Image, ImageFilter, ImageStat
    with Image.open(io.BytesIO(jpeg)) as source:
        image = source.convert("L")
        image.thumbnail((320, 180))
        stats = ImageStat.Stat(image)
        brightness = stats.mean[0]
        contrast = stats.stddev[0]
        edges = ImageStat.Stat(image.filter(ImageFilter.FIND_EDGES)).mean[0]
    # Penalize blank, very dark and overexposed frames.
    exposure = max(0.0, 1.0 - abs(brightness - 125.0) / 125.0)
    return contrast * 0.7 + edges * 0.5 + exposure * 18.0


def extract_long_cover(video):
    """Select a clear real video frame for the custom long-form thumbnail."""
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
    # Seek across the hook and early story, not just a single fixed timestamp.
    timestamps = sorted(set(min(duration / 2, max(0.0, duration * fraction))
                            for fraction in (0.03, 0.08, 0.14, 0.22, 0.30)))
    candidates = []
    for timestamp in timestamps:
        try:
            result = subprocess.run(
                ["ffmpeg", "-hide_banner", "-loglevel", "error",
                 "-ss", f"{timestamp:.3f}", "-i", str(video),
                 "-frames:v", "1", "-vf",
                 "scale=1280:720:force_original_aspect_ratio=increase,crop=1280:720",
                 "-q:v", "3", "-f", "image2pipe", "-vcodec", "mjpeg", "-"],
                capture_output=True, timeout=30, check=True,
            )
            if result.stdout and len(result.stdout) <= 2 * 1024 * 1024:
                candidates.append((_frame_score(result.stdout), result.stdout))
        except (subprocess.SubprocessError, OSError, ValueError):
            continue
    if not candidates:
        raise RuntimeError("No valid thumbnail frames")
    print("ASTRA_LONG_COVER_SAMPLES=" + str(len(candidates)))
    destination = video.with_name(video.stem + "_cover_wide.jpg")
    winner = max(candidates, key=lambda item: item[0])
    destination.write_bytes(winner[1])
    print("ASTRA_LONG_COVER_SCORE=" + f"{winner[0]:.2f}")
    if not 0 < destination.stat().st_size <= 2 * 1024 * 1024:
        raise RuntimeError("Invalid long-form cover")
    return destination
