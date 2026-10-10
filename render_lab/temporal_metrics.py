"""Inspect sampled video frames for pixel changes, not character animation."""
import json
import subprocess
from io import BytesIO
from pathlib import Path
from PIL import Image, ImageChops, ImageStat

def measure(video, times=None):
    probe = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
        "format=duration", "-of", "json", str(video)],
        capture_output=True, text=True, check=True, timeout=20)
    duration = float(json.loads(probe.stdout)["format"]["duration"])
    if duration <= 0.5:
        raise ValueError("Video too short for temporal analysis")
    if times is None:
        times = [round(duration * fraction, 3) for fraction in (0.1, 0.25, 0.4, 0.6, 0.75, 0.9)]
    times = [t for t in times if 0 <= t < duration - 0.05]
    if len(times) < 2:
        raise ValueError("Need at least two valid sample times")
    frames = []
    for second in times:
        result = subprocess.run(["ffmpeg", "-v", "error", "-ss", str(second),
            "-i", str(video), "-frames:v", "1", "-vf", "scale=128:128",
            "-f", "image2pipe", "-vcodec", "png", "-"],
            capture_output=True, check=True, timeout=45)
        with Image.open(BytesIO(result.stdout)) as img:
            frames.append(img.convert("RGB").copy())
    differences = []
    for first, second in zip(frames, frames[1:]):
        stat = ImageStat.Stat(ImageChops.difference(first, second))
        differences.append(round(sum(stat.mean) / 3, 2))
    return {"duration_seconds": round(duration, 3), "sample_times_seconds": times,
            "frame_differences": differences,
            "near_static_intervals": sum(d < 0.5 for d in differences),
            "character_motion_verified": False,
            "note": "Pixel change can come from camera movement or cuts."}

if __name__ == "__main__":
    import sys
    print(json.dumps(measure(Path(sys.argv[1])), indent=2))
