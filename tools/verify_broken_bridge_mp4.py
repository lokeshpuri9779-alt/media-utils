"""Review-only decoded-MP4 evidence for the Fox/Rabbit broken-plank scene.

A fixed 1080x1920 QA-fixture regression; not semantic approval or permission to publish.
"""
import argparse
import hashlib
import io
import json
import subprocess
from pathlib import Path

from PIL import Image

SAMPLE_TIME_SEC = 7.5
SAMPLES = {"left_deck": (200, 1160), "right_deck": (940, 1160),
           "open_water": (550, 1150), "fallen_plank": (640, 1205)}


def _wood(rgb):
    r, g, b = rgb
    return 115 <= r <= 240 and 65 <= g <= 190 and 35 <= b <= 140 and r > 1.24 * g and g > 1.08 * b


def _water(rgb):
    r, g, b = rgb
    return 25 <= r <= 95 and 65 <= g <= 190 and 80 <= b <= 205 and b > 1.45 * r and g > 1.4 * r


def frame_evidence(image):
    if image.size != (1080, 1920):
        raise ValueError("Broken-bridge QA requires encoded 1080x1920 master")
    rgb = image.convert("RGB")
    colors = {name: rgb.getpixel(xy) for name, xy in SAMPLES.items()}
    checks = {"left_deck_wood": _wood(colors["left_deck"]),
              "right_deck_wood": _wood(colors["right_deck"]),
              "missing_plank_open_water": _water(colors["open_water"]),
              "broken_fragment_visible": _wood(colors["fallen_plank"])}
    return {"pass": all(checks.values()), "checks": checks,
            "sample_rgb": {k: list(v) for k, v in colors.items()}}


def verify_video(path):
    from imageio_ffmpeg import get_ffmpeg_exe
    command = [get_ffmpeg_exe(), "-hide_banner", "-loglevel", "error",
               "-ss", str(SAMPLE_TIME_SEC), "-i", str(path), "-frames:v",
               "1", "-f", "image2pipe", "-vcodec", "png", "-"]
    result = subprocess.run(command, check=True, capture_output=True, timeout=60)
    if not result.stdout:
        raise ValueError("No decoded MP4 video frame")
    with Image.open(io.BytesIO(result.stdout)) as image:
        report = frame_evidence(image)
    report.update(sample_time_sec=SAMPLE_TIME_SEC,
                  mp4_sha256=hashlib.sha256(Path(path).read_bytes()).hexdigest(),
                  production_approved=False, publication_triggered=False)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("video", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = verify_video(args.video)
    print("ASTRA_BROKEN_BRIDGE_MP4_EVIDENCE=" + json.dumps(report, sort_keys=True))
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    if not report["pass"]:
        raise SystemExit("Decoded MP4 lacks broken-plank evidence")


if __name__ == "__main__":
    main()
