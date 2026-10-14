"""Offline media quality evidence; never grants publishing permission."""
import json
import subprocess
from pathlib import Path
import imageio_ffmpeg


def audit_story(output, expected_seconds=10):
    output = Path(output)
    video = output / "preview.mp4"
    report_path = output / "batch-result.json"
    if not video.is_file() or not report_path.is_file():
        raise FileNotFoundError("Missing video or story report")
    report = json.loads(report_path.read_text())
    cmd = [imageio_ffmpeg.get_ffmpeg_exe(), "-hide_banner", "-i", str(video)]
    probe = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    details = probe.stderr
    import re
    duration = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", details)
    seconds = (int(duration[1]) * 3600 + int(duration[2]) * 60 +
               float(duration[3])) if duration else None
    checks = {
        "file_nonempty": video.stat().st_size > 1000,
        "subtitles_present": (output / "captions.srt").is_file() and
                             (output / "captions.srt").stat().st_size > 20,
        "video_h264": "Video: h264" in details,
        "audio_aac": "Audio: aac" in details,
        "duration_matches": seconds is not None and abs(seconds - expected_seconds) < 0.5,
        "motion_gate": not report.get("motion_failures"),
        "scene_openings_unique": not report.get("visually_duplicate_scene_openings"),
        "publication_disabled": report.get("publication_allowed") is False,
        "quality_unapproved": report.get("quality_approved") is False,
    }
    audit = {
        "title": report.get("title"),
        "checks": checks,
        "all_checks_passed": all(checks.values()),
        "duration_seconds": seconds,
        "video_bytes": video.stat().st_size,
        "creative_quality_verified": False,
        "publication_allowed": False,
        "note": "Technical pass is not creative approval or permission to upload.",
    }
    (output / "quality-audit.json").write_text(json.dumps(audit, indent=2))
    if not audit["all_checks_passed"]:
        raise RuntimeError(f"Technical quality gate failed: {checks}")
    return audit


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    parser.add_argument("--expected-seconds", type=float, default=10)
    args = parser.parse_args()
    print(json.dumps(audit_story(args.output, args.expected_seconds), indent=2))
