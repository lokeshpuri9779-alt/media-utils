"""Validate the actual long-form trend renderer output and its audio/video streams."""
import json
import re
import subprocess
import sys
from pathlib import Path

from imageio_ffmpeg import get_ffmpeg_exe


def run(*args):
    return subprocess.run(args, check=True, capture_output=True, text=True)


def verify(video_path):
    video = Path(video_path)
    report_path = video.with_suffix(".json")
    if not video.is_file() or video.stat().st_size < 100_000:
        raise ValueError("Long-form QA MP4 missing or unexpectedly small")
    if not report_path.is_file():
        raise ValueError("Long-form renderer report is missing")
    report = json.loads(report_path.read_text(encoding="utf-8"))
    if report.get("format") != "long" or report.get("resolution") != [1920, 1080]:
        raise ValueError("Expected 1920x1080 landscape long-form output")
    if int(report.get("fps", 0)) != 30 or float(report.get("duration", 0)) < 90:
        raise ValueError("Expected 30 FPS long-form video of at least 90 seconds")
    pacing = report.get("pacing_profile") or {}
    expected = {"name": "high-energy", "voice_speed": 1.14,
                "caption_words_per_change": 6, "visual_transition_seconds": 0.14,
                "target_music_bpm": 128}
    for key, value in expected.items():
        if pacing.get(key) != value:
            raise ValueError("Pacing mismatch for " + key)
    if report.get("scene_count") != 8 or len(report.get("story_beats") or []) < 6:
        raise ValueError("Long-form story structure is incomplete")
    if len(report.get("sources") or []) < 2:
        raise ValueError("Expected two source references in synthetic fixture")
    ffmpeg = get_ffmpeg_exe()
    metadata = run(ffmpeg, "-hide_banner", "-i", str(video), "-f", "null", "-")
    stream_info = metadata.stderr
    if "Video:" not in stream_info or "Audio:" not in stream_info or "1920x1080" not in stream_info:
        raise ValueError("MP4 must contain 1920x1080 video and narration audio")
    if not re.search(r"30\s*fps", stream_info):
        raise ValueError("MP4 stream does not report 30 FPS")
    run(ffmpeg, "-v", "error", "-i", str(video), "-map", "0:v:0", "-f", "null", "-")
    run(ffmpeg, "-v", "error", "-i", str(video), "-map", "0:a:0", "-f", "null", "-")
    return {"status": "pass", "bytes": video.stat().st_size,
            "duration": report["duration"], "resolution": report["resolution"],
            "fps": report["fps"], "audio": "present_and_decoded",
            "pacing_profile": pacing, "story_beats": report["story_beats"]}


if __name__ == "__main__":
    print(json.dumps(verify(sys.argv[1]), sort_keys=True))
