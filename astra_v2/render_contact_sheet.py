"""Bounded, review-only sampled frames from a locally rendered MP4.

The contact sheet is evidence for human inspection, not a semantic pass or
publication approval. It never accesses YouTube or a paid image API.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
import av

from PIL import Image, ImageDraw


def create_contact_sheet(video_path, output_path, *, duration_seconds=None, frame_count=4,
                         sample_times_seconds=None):
    """Sample a few actual decoded frames; fail rather than invent evidence."""
    video = Path(video_path)
    output = Path(output_path)
    if not video.is_file() or video.stat().st_size == 0:
        raise ValueError("missing_nonempty_video")
    if frame_count != 4:
        raise ValueError("review_sheet_requires_four_samples")
    try:
        container = av.open(str(video), mode="r")
    except Exception as exc:
        raise RuntimeError("video_decode_unavailable") from exc
    with container:
        video_stream = next(iter(container.streams.video), None)
        if video_stream is None:
            raise ValueError("missing_video_stream")
        if duration_seconds is None:
            if video_stream.duration is not None and video_stream.time_base is not None:
                duration_seconds = float(video_stream.duration * video_stream.time_base)
            elif container.duration is not None:
                duration_seconds = float(container.duration / av.time_base)
            else:
                raise ValueError("video_duration_unavailable")
        duration = float(duration_seconds)
        if not math.isfinite(duration) or not 0 < duration <= 3600:
            raise ValueError("invalid_video_duration")
        if sample_times_seconds is None:
            times = [round(duration * (2 * i + 1) / (2 * frame_count), 3)
                     for i in range(frame_count)]
            strategy = "uniform_quartiles"
        else:
            if (not isinstance(sample_times_seconds, (list, tuple))
                    or len(sample_times_seconds) != frame_count
                    or any(type(t) not in (int, float) or not math.isfinite(t)
                           or t < 0 or t >= duration for t in sample_times_seconds)):
                raise ValueError("invalid_storybeat_sample_times")
            times = [round(t, 3) for t in sample_times_seconds]
            if any(a >= b for a, b in zip(times, times[1:])):
                raise ValueError("overlapping_storybeat_sample_times")
            strategy = "planned_beat_midpoints"
        sheet = Image.new("RGB", (720, 1280), (24, 24, 24))
        for i, timestamp in enumerate(times):
            try:
                offset = int(timestamp / float(video_stream.time_base))
                container.seek(offset, stream=video_stream, backward=True, any_frame=False)
                selected = None
                for frame in container.decode(video_stream):
                    if frame.pts is not None:
                        frame_time = float(frame.pts * video_stream.time_base)
                        if frame_time >= timestamp:
                            selected = frame
                            break
                    selected = frame
                if selected is None:
                    raise RuntimeError("missing_decoded_frame")
                shot = selected.to_image().convert("RGB")
                shot.thumbnail((360, 640), Image.Resampling.LANCZOS)
                tile = Image.new("RGB", (360, 640), (0, 0, 0))
                tile.paste(shot, ((360 - shot.width) // 2, (640 - shot.height) // 2))
                sheet.paste(tile, ((i % 2) * 360, (i // 2) * 640))
            except Exception as exc:
                if isinstance(exc, RuntimeError) and str(exc) == "missing_decoded_frame":
                    raise
                raise RuntimeError("frame_decode_failed") from exc
    draw = ImageDraw.Draw(sheet)
    for i, timestamp in enumerate(times):
        x, y = (i % 2) * 360, (i // 2) * 640
        draw.rectangle((x, y, x + 135, y + 24), fill=(0, 0, 0))
        draw.text((x + 8, y + 5), f"Sample {i + 1}  {timestamp:.1f}s", fill=(255, 255, 255))
    output.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output, format="JPEG", quality=78, optimize=True)
    # Bind the exact sampled JPEG as well as its source MP4. A replacement
    # contact sheet with unchanged JSON must not pass independent inspection.
    sheet_sha256 = hashlib.sha256(output.read_bytes()).hexdigest()
    digest = hashlib.sha256()
    with video.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    manifest = {
        "schema_version": 1,
        "source_mp4_sha256": digest.hexdigest(),
        "contact_sheet_sha256": sheet_sha256,
        "sample_times_seconds": times,
        "sample_strategy": strategy,
        "sample_count": frame_count,
        "visual_review": "required",
        "semantic_quality": "not_verified",
        "publication_approval": False,
        "evidence_scope": "Four sampled decoded frames, not a complete video or semantic pass",
    }
    output.with_suffix(".json").write_text(
        json.dumps(manifest, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return {"path": str(output), "manifest": str(output.with_suffix(".json")),
            "source_mp4_sha256": digest.hexdigest(), "contact_sheet_sha256": sheet_sha256,
            "sample_count": frame_count, "sample_strategy": strategy,
            "semantic_quality": "not_verified"}
