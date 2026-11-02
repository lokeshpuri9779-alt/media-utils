"""Bounded pixel-level evidence for isolated ASTRA spark-to-beacon previews.

Checks a fixed, intentionally stylized experiment's rendered RGB pixels.
This is not AI/semantic quality assessment, approval, or a production gate.
"""
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

WIDTH, HEIGHT, FRAMES = 384, 576, 20
OUTPUT = Path("artifacts/experimental-causal-story")


def decode_frames(directory: Path):
    """Decode existing PNGs using the workflow's free FFmpeg dependency."""
    proc = subprocess.run(
        [
            "ffmpeg", "-hide_banner", "-loglevel", "error",
            "-framerate", "8", "-start_number", "0", "-i",
            str(directory / "frame_%03d.png"), "-frames:v", str(FRAMES),
            "-f", "rawvideo", "-pix_fmt", "rgb24", "pipe:1",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )
    frame_bytes = WIDTH * HEIGHT * 3
    expected = FRAMES * frame_bytes
    if len(proc.stdout) != expected:
        raise ValueError(
            f"Expected {expected} RGB bytes, got {len(proc.stdout)}"
        )
    return [
        memoryview(proc.stdout)[i * frame_bytes:(i + 1) * frame_bytes]
        for i in range(FRAMES)
    ]


def amber_pixels(frame, roi):
    """Locate high-contrast warm emissive pixels in a predefined story area."""
    left, top, right, bottom = roi
    if not (0 <= left < right <= WIDTH and 0 <= top < bottom <= HEIGHT):
        raise ValueError("ROI outside fixed story frame")
    found = []
    for y in range(top, bottom):
        for x in range(left, right):
            off = 3 * (y * WIDTH + x)
            r, g, b = frame[off], frame[off + 1], frame[off + 2]
            if r >= 195 and g >= 140 and b <= 170 and r * 10 >= 13 * b and g * 10 >= 12.5 * b:
                found.append((x, y))
    return {"count": len(found),
            "min_x": min((x for x, _ in found), default=None),
            "max_x": max((x for x, _ in found), default=None)}


def score_frames(frames, render_report):
    """Evaluate raw rendered frames; return testable evidence without file I/O.

    Separate this from the CLI so deliberately damaged rendered frames can be
    rejected in regression tests. This remains a fixed-scene, limited proxy.
    """
    if len(frames) != FRAMES:
        raise ValueError(f"Expected exactly {FRAMES} frames")
    if any(len(frame) != WIDTH * HEIGHT * 3 for frame in frames):
        raise ValueError("Unexpected RGB frame size")

    # Within payoff shot only, the camera is fixed at 34mm. The travelling
    # beam crosses this unobstructed sky corridor toward the left lighthouse.
    sky_roi = (70, 175, 310, 290)
    # A narrow crop around the lighthouse beacon: incoming beam appears
    # first; full emission rings appear strictly after beam contact.
    beacon_roi = (50, 130, 140, 225)
    sky = {str(i): amber_pixels(frames[i], sky_roi) for i in range(15, 20)}
    beacon = {str(i): amber_pixels(frames[i], beacon_roi) for i in range(15, 20)}
    minimum_x = [sky[str(i)]["min_x"] for i in (15, 16, 17)]
    b15, b16, b17, b18, b19 = (
        beacon[str(i)]["count"] for i in range(15, 20)
    )

    checks = {
        "same_review_only_source": (
            render_report.get("success") is True
            and len(render_report.get("frames", [])) == FRAMES
            and render_report.get("production_ready") is False
            and render_report.get("approved") is False
            and render_report.get("published") is False
            and render_report.get("paid_apis_used") is False
            and render_report.get("visual_review_required") is True
        ),
        "physical_energy_pixels_rendered": (
            all(sky[str(i)]["count"] > 200 for i in (15, 16, 17))
        ),
        "beam_front_moves_toward_lighthouse": (
            all(x is not None for x in minimum_x)
            and minimum_x[0] - minimum_x[1] >= 25
            and minimum_x[1] - minimum_x[2] >= 25
        ),
        "beacon_stays_visually_dark_during_launch": max(b15, b16) <= 25,
        "incoming_beam_visible_at_target_before_ignition": (
            b17 >= 50 and b17 > b16 + 30
        ),
        "beacon_visibly_ignites_after_contact": (
            b18 >= 400 and b18 >= b17 * 3
        ),
        "beacon_glow_persists_last_frame": (
            b19 >= 400 and abs(b19 - b18) < max(150, b18 * .25)
        ),
        "source_beacon_states_match_visual_sequence": (
            [bool(f["beacon_on"]) for f in render_report["frames"]]
            == [False] * 18 + [True] * 2
        ),
    }
    result = {
        "experiment": "isolated fixed-shot emissive pixel regression",
        "note": "Stylized, fixed-ROI image proxy; cannot establish story clarity or cinematic quality.",
        "passes_fixed_pixel_checks": all(checks.values()),
        "approved": False,
        "published": False,
        "production_ready": False,
        "paid_apis_used": False,
        "manual_editorial_review_required": True,
        "visual_semantic_quality": "not_verified",
        "frames": FRAMES,
        "sky_roi": list(sky_roi),
        "beacon_roi": list(beacon_roi),
        "sky_evidence": sky,
        "beacon_evidence": beacon,
        "checks": checks,
    }
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--directory", type=Path, default=OUTPUT)
    args = parser.parse_args()
    directory = args.directory
    render_report = json.loads(
        (directory / "review.json").read_text(encoding="utf-8")
    )
    frames = decode_frames(directory)
    result = score_frames(frames, render_report)
    (directory / "visual_audit.json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8"
    )
    print("ASTRA_CAUSAL_VISUAL_AUDIT=" + json.dumps(result), flush=True)
    if not result["passes_fixed_pixel_checks"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
