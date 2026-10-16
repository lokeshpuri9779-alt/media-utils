"""Validate a Studio preview with mandatory audio, video and scene integrity."""
import json
import re
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageStat
from imageio_ffmpeg import get_ffmpeg_exe


def run(*args):
    return subprocess.run(args, check=True, capture_output=True, text=True)


def verify(video):
    video = Path(video)
    if not video.is_file() or video.stat().st_size < 10000:
        raise ValueError("Studio MP4 missing or too small")
    ff = get_ffmpeg_exe()
    metadata = run(ff, "-hide_banner", "-i", str(video), "-f", "null", "-")
    stream_info = metadata.stderr
    if "Video:" not in stream_info or "Audio:" not in stream_info:
        raise ValueError("Studio MP4 must contain both video and narration audio")
    run(ff, "-v", "error", "-i", str(video), "-map", "0:v:0", "-f", "null", "-")
    run(ff, "-v", "error", "-i", str(video), "-map", "0:a:0", "-f", "null", "-")

    # Stream presence and successful decoding do not prove that narration is audible.
    levels = run(ff, "-hide_banner", "-i", str(video), "-map", "0:a:0",
                 "-af", "volumedetect", "-f", "null", "-")
    match = re.search(r"max_volume:\s*(-?inf|[-+]?\d+(?:\.\d+)?)\s*dB",
                      levels.stderr, re.IGNORECASE)
    if not match:
        raise ValueError("Could not measure Studio audio level")
    max_volume = float("-inf") if match.group(1).lower() == "-inf" else float(match.group(1))
    if max_volume <= -60.0:
        raise ValueError(f"Studio narration is silent or nearly silent (max_volume={max_volume} dB)")

    report = video.with_suffix(".json")
    if report.exists():
        data = json.loads(report.read_text(encoding="utf-8"))
        if data.get("frames", 0) <= 0 or data.get("duration", 0) <= 0:
            raise ValueError("Invalid Studio render report")
    frame = video.with_name("studio-frame.png")
    run(ff, "-v", "error", "-y", "-ss", "0.5", "-i", str(video),
        "-frames:v", "1", str(frame))
    im = Image.open(frame).convert("RGB")
    if im.size != (1080, 1920):
        raise ValueError(f"Incorrect resolution: {im.size}")
    if max(ImageStat.Stat(im.resize((108, 192))).stddev) < 2:
        raise ValueError("Preview frame is nearly uniform")
    return {"status": "pass", "bytes": video.stat().st_size,
            "resolution": list(im.size), "video_decode": "passed",
            "audio_stream": "present_and_decoded", "audio_max_volume_db": max_volume,
            "report_present": report.exists()}


if __name__ == "__main__":
    print(json.dumps(verify(sys.argv[1])))
