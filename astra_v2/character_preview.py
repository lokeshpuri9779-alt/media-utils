"""Render a small, inspectable ASTRA animation sample without GPU or API keys."""
from pathlib import Path
import math
import subprocess
import tempfile
from PIL import Image
from astra_v2.story_visuals import draw_subject

SUBJECTS = ("dog", "monkey", "bird", "rabbit")


def main():
    destination = Path("runtime-health/astra-character-preview.mp4")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="astra-preview-") as tmp:
        frames = Path(tmp)
        fps = 6
        for index in range(4 * fps * len(SUBJECTS)):
            subject = SUBJECTS[index // (4 * fps)]
            t = (index % (4 * fps)) / fps
            image = Image.new("RGB", (1080, 1920), (24, 34, 52))
            draw_subject(image, subject, t, (236, 174, 112))
            image.resize((360, 640), Image.Resampling.BILINEAR).save(
                frames / f"{index:04d}.jpg", quality=75)
        subprocess.run([
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
            "-framerate", str(fps), "-i", str(frames / "%04d.jpg"),
            "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
            "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-shortest", "-movflags", "+faststart",
            str(destination)
        ], check=True, timeout=120)
    if destination.stat().st_size < 10_000:
        raise RuntimeError("Preview output too small")
    print("ASTRA_CHARACTER_PREVIEW=" + str(destination))


if __name__ == "__main__":
    main()
