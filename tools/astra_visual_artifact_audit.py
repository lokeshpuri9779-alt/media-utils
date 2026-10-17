"""Objective visual artifact diagnostics for ASTRA QA videos.

Samples decoded frames with FFmpeg. Findings are REVIEW SIGNALS, not a
subjective visual-quality score or an automatic YouTube publishing decision.
"""
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

import numpy as np
from imageio_ffmpeg import get_ffmpeg_exe

SAMPLE_FPS = 6
SAMPLE_SIZE = (96, 170)


def audit_samples(frames, fps=SAMPLE_FPS):
    """Find obvious blank runs, held frames and one-frame luminance flashes."""
    arr = np.asarray(frames, dtype=np.uint8)
    if not (0 < fps <= 120):
        raise ValueError("fps must be between 0 and 120")
    if arr.ndim != 3 or arr.shape[0] < 2 or not arr.shape[1] or not arr.shape[2]:
        raise ValueError("Need at least two nonempty grayscale frames (N,H,W)")
    means = arr.mean(axis=(1, 2))
    dark = (arr < 12).mean(axis=(1, 2)) > .985
    bright = (arr > 245).mean(axis=(1, 2)) > .985
    diffs = np.abs(arr[1:].astype(np.int16) - arr[:-1].astype(np.int16)).mean(axis=(1, 2))
    warnings = []

    def runs(mask, label, minimum):
        start = None
        for i in range(len(mask) + 1):
            active = i < len(mask) and bool(mask[i])
            if active and start is None:
                start = i
            if not active and start is not None:
                seconds = (i - start) / fps
                if seconds >= minimum:
                    warnings.append({"type": label, "at_seconds": round(start / fps, 2),
                                     "duration_seconds": round(seconds, 2)})
                start = None

    runs(dark, "nearly_black_frames", 1.0)
    runs(bright, "nearly_white_frames", 1.0)
    # Both horizontal edges black while the central picture is present:
    # a diagnostic for unintended letterboxing in a vertical Short.
    edge_rows = max(1, arr.shape[1] // 20)
    edge_dark = ((arr[:, :edge_rows, :] < 12).mean(axis=(1, 2)) > .97) & \
                ((arr[:, -edge_rows:, :] < 12).mean(axis=(1, 2)) > .97)
    middle = arr[:, edge_rows:-edge_rows, :] if arr.shape[1] > 2 * edge_rows else arr
    edge_bars = edge_dark & (middle.mean(axis=(1, 2)) > 35)
    runs(edge_bars, "horizontal_black_bars", 2.0)
    # Consecutive frame-pair differences are not independent scene boundaries.
    runs(diffs < .35, "near_frozen_frames", 3.0)
    # Repeated A/B/A brightness changes may indicate unintended flicker.
    # These are review candidates, not proof of a rendering defect.
    if len(means) >= 5:
        delta = np.diff(means)
        alternating = ((delta[:-1] * delta[1:] < 0)
                       & (np.abs(delta[:-1]) >= 30)
                       & (np.abs(delta[1:]) >= 30)
                       & (np.abs(means[:-2] - means[2:]) <= 15))
        runs(alternating, "alternating_luminance_flicker", .5)
    # A single bright/dark spike returning to its original level is more
    # suspicious than a legitimate sustained lighting change or scene cut.
    for i in range(1, len(means) - 1):
        if (abs(means[i] - means[i-1]) >= 75
                and abs(means[i] - means[i+1]) >= 75
                and abs(means[i-1] - means[i+1]) <= 20):
            warnings.append({"type": "single_sample_luminance_flash",
                             "at_seconds": round(i / fps, 2)})
    return {"samples": int(len(arr)), "warnings": warnings,
            "status": "review_needed" if warnings else "no_obvious_artifacts"}


def decode_samples(video: Path, fps=SAMPLE_FPS):
    if not video.is_file():
        raise FileNotFoundError(video)
    width, height = SAMPLE_SIZE
    cmd = [get_ffmpeg_exe(), "-hide_banner", "-loglevel", "error",
           "-i", str(video), "-vf", f"fps={fps},scale={width}:{height}",
           "-pix_fmt", "gray", "-f", "rawvideo", "-"]
    proc = subprocess.run(cmd, capture_output=True, timeout=120, check=True)
    frame_bytes = width * height
    if len(proc.stdout) % frame_bytes:
        raise RuntimeError("Incomplete decoded frame data")
    if len(proc.stdout) < 2 * frame_bytes:
        raise RuntimeError("Too few decoded frames to audit")
    return np.frombuffer(proc.stdout, dtype=np.uint8).reshape((-1, height, width))


def audit_videos(paths):
    results = {}
    for path in paths:
        try:
            results[str(path)] = audit_samples(decode_samples(path))
        except (OSError, RuntimeError, ValueError, subprocess.SubprocessError) as exc:
            results[str(path)] = {"status": "unavailable", "warnings": [],
                                  "error": str(exc)[:240]}
    return {"version": 2, "sample_fps": SAMPLE_FPS,
            "purpose": "Objective diagnostic evidence; human visual review still required",
            "videos": results}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("videos", nargs="+", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = audit_videos(args.videos)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    if any(v["status"] == "unavailable" for v in report["videos"].values()):
        raise SystemExit(2)


if __name__ == "__main__":
    main()
