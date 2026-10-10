"""Inspect sampled video frames for pixel changes, not character animation."""
import json
import subprocess
from io import BytesIO
from pathlib import Path
from PIL import Image, ImageChops, ImageStat

def measure(video, times=(0.5, 1.5, 2.5, 3.5, 4.5, 5.5)):
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
    return {"frame_differences": differences,
            "character_motion_verified": False,
            "note": "Pixel change can come from camera movement or cuts."}

if __name__ == "__main__":
    import sys
    print(json.dumps(measure(Path(sys.argv[1])), indent=2))
