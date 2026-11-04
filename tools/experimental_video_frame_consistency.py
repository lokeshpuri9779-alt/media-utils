"""Check that a review MP4 depicts the corresponding rendered PNG sequence.

Lossy H.264 cannot match PNGs byte-for-byte. Decode both to RGB24 with the
existing free FFmpeg tool, then bound per-frame mean absolute pixel error.
This is a technical *content correspondence* test, not semantic validation,
authenticity, cinematography or permission to publish.
"""
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

WIDTH, HEIGHT, FPS = 384, 576, 8
FRAME_BYTES = WIDTH * HEIGHT * 3
MAX_FRAME_RGB_MAE = 6.0
MAX_MEAN_RGB_MAE = 4.5


def decode_rgb(source, count, *, png_sequence=False):
    if count not in (20, 32):
        raise ValueError("Only existing isolated review frame counts are supported")
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error"]
    if png_sequence:
        cmd.extend(["-framerate", str(FPS), "-start_number", "0"])
    cmd.extend(["-i", str(source), "-frames:v", str(count), "-f", "rawvideo",
                "-pix_fmt", "rgb24", "-"])
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            timeout=45, check=True)
    if len(result.stdout) != count * FRAME_BYTES:
        raise ValueError(
            f"Decoded RGB24 size mismatch: expected {count * FRAME_BYTES} "
            f"bytes, got {len(result.stdout)}"
        )
    return result.stdout


def compare_decoded(reference, encoded, count, *, frame_bytes=FRAME_BYTES):
    """Compare ordered RGB frames, without metadata-based assumptions."""
    if not isinstance(reference, (bytes, bytearray, memoryview)) or not isinstance(
            encoded, (bytes, bytearray, memoryview)):
        raise ValueError("Both decoded streams must be RGB bytes")
    if count < 1 or frame_bytes < 1 or (
            len(reference) != count * frame_bytes
            or len(encoded) != count * frame_bytes):
        raise ValueError("Incomplete, excess, or corrupt decoded RGB frame stream")
    ref, enc = memoryview(reference), memoryview(encoded)
    means = []
    for frame in range(count):
        lo, hi = frame * frame_bytes, (frame + 1) * frame_bytes
        total = sum(abs(a - b) for a, b in zip(ref[lo:hi], enc[lo:hi]))
        means.append(round(total / frame_bytes, 4))
    worst = max(range(count), key=lambda i: means[i])
    overall = round(sum(means) / count, 4)
    checks = {
        "correct_number_of_decoded_frames": True,
        "every_video_frame_matches_its_png": all(
            mean <= MAX_FRAME_RGB_MAE for mean in means
        ),
        "average_visual_difference_within_limit": overall <= MAX_MEAN_RGB_MAE,
    }
    return {
        "passed": all(checks.values()),
        "checks": checks,
        "mean_rgb_mae": overall,
        "max_frame_rgb_mae": means[worst],
        "worst_frame": worst,
        "per_frame_rgb_mae": means,
        "limit_max_frame_rgb_mae": MAX_FRAME_RGB_MAE,
        "limit_mean_rgb_mae": MAX_MEAN_RGB_MAE,
        "evidence_scope": "decoded RGB24 frame-by-frame fidelity, not semantics",
    }


def compare_video(directory, video_name, count):
    root = Path(directory)
    # Do not silently consume an arbitrary second video file.
    if video_name not in ("story_previs.mp4", "frog_story_previs.mp4"):
        raise ValueError("Unsupported isolated preview video name")
    pngs = root / "frame_%03d.png"
    movie = root / video_name
    if not movie.is_file():
        raise FileNotFoundError("Missing preview video")
    if any(not (root / f"frame_{i:03d}.png").is_file() for i in range(count)):
        raise FileNotFoundError("Missing source PNG frame")
    original = decode_rgb(pngs, count, png_sequence=True)
    rendered_video = decode_rgb(movie, count)
    return compare_decoded(original, rendered_video, count)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", choices=("frog", "lighthouse"), required=True)
    parser.add_argument("--directory", type=Path, required=True)
    args = parser.parse_args()
    profile = {"frog": ("frog_story_previs.mp4", 32),
               "lighthouse": ("story_previs.mp4", 20)}
    name, count = profile[args.profile]
    evidence = compare_video(args.directory, name, count)
    result = {
        "profile": args.profile, **evidence,
        "approved": False, "published": False,
        "production_ready": False, "paid_apis_used": False,
        "manual_visual_review_required": True,
        "semantic_quality": "not_verified",
    }
    print("ASTRA_VIDEO_FRAME_CORRESPONDENCE=" + json.dumps(result), flush=True)
    if not result["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
