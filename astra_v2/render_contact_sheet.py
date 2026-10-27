"""Bounded, review-only sampled frames from a locally rendered MP4.

The contact sheet is evidence for human inspection, not a semantic pass or
publication approval. It never accesses YouTube or a paid image API.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
import shutil
import subprocess
import tempfile

from PIL import Image, ImageDraw


def create_contact_sheet(video_path, output_path, *, duration_seconds=None, frame_count=4):
    """Sample a few actual decoded frames; fail rather than invent evidence."""
    video = Path(video_path)
    output = Path(output_path)
    if not video.is_file() or video.stat().st_size == 0:
        raise ValueError("missing_nonempty_video")
    if duration_seconds is None:
        ffprobe = shutil.which("ffprobe")
        if not ffprobe:
            raise RuntimeError("ffprobe_unavailable")
        probe = subprocess.run(
            [ffprobe, "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", str(video)],
            check=True, timeout=15, capture_output=True, text=True)
        duration_seconds = probe.stdout.strip()
    duration = float(duration_seconds)
    if not math.isfinite(duration) or not 0 < duration <= 3600:
        raise ValueError("invalid_video_duration")
    if frame_count != 4:
        raise ValueError("review_sheet_requires_four_samples")
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("ffmpeg_unavailable")
    times = [round(duration * (2 * i + 1) / (2 * frame_count), 3)
             for i in range(frame_count)]
    sheet = Image.new("RGB", (720, 1280), (24, 24, 24))
    with tempfile.TemporaryDirectory(prefix="astra-review-frames-") as directory:
        for i, timestamp in enumerate(times):
            frame = Path(directory) / f"frame-{i}.jpg"
            command = [ffmpeg, "-nostdin", "-hide_banner", "-loglevel", "error",
                       "-ss", f"{timestamp:.3f}", "-i", str(video),
                       "-frames:v", "1", "-vf",
                       "scale=360:640:force_original_aspect_ratio=decrease,"
                       "pad=360:640:(ow-iw)/2:(oh-ih)/2", "-y", str(frame)]
            subprocess.run(command, check=True, timeout=15,
                           stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
            if not frame.is_file() or frame.stat().st_size == 0:
                raise RuntimeError("missing_decoded_frame")
            with Image.open(frame) as decoded:
                shot = decoded.convert("RGB")
                if shot.size != (360, 640):
                    raise RuntimeError("unexpected_sample_size")
                sheet.paste(shot, ((i % 2) * 360, (i // 2) * 640))
    draw = ImageDraw.Draw(sheet)
    for i, timestamp in enumerate(times):
        x, y = (i % 2) * 360, (i // 2) * 640
        draw.rectangle((x, y, x + 135, y + 24), fill=(0, 0, 0))
        draw.text((x + 8, y + 5), f"Sample {i + 1}  {timestamp:.1f}s", fill=(255, 255, 255))
    output.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output, format="JPEG", quality=78, optimize=True)
    digest = hashlib.sha256()
    with video.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    manifest = {
        "schema_version": 1,
        "source_mp4_sha256": digest.hexdigest(),
        "sample_times_seconds": times,
        "sample_count": frame_count,
        "visual_review": "required",
        "semantic_quality": "not_verified",
        "publication_approval": False,
        "evidence_scope": "Four sampled decoded frames, not a complete video or semantic pass",
    }
    output.with_suffix(".json").write_text(
        json.dumps(manifest, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return {"path": str(output), "manifest": str(output.with_suffix(".json")),
            "source_mp4_sha256": digest.hexdigest(), "sample_count": frame_count,
            "semantic_quality": "not_verified"}
