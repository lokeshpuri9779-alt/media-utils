"""Create optional burned-in captions for an assembled ASTRA video.

SRT is provided by the story/voiceover pipeline; no transcription is invented.
"""
from __future__ import annotations
import argparse
import json
import shutil
import subprocess
from pathlib import Path

def caption(video: Path, subtitles: Path, output: Path) -> dict:
    if not video.is_file() or not subtitles.is_file():
        raise FileNotFoundError("Video and SRT captions must exist")
    if subtitles.suffix.lower() != ".srt":
        raise ValueError("Captions must be an SRT file")
    if not subtitles.read_text(encoding="utf-8-sig").strip():
        raise ValueError("SRT file is empty")
    if not shutil.which("ffmpeg"):
        raise RuntimeError("FFmpeg is required")
    if video.resolve() == output.resolve():
        raise ValueError("Output must differ from source video")
    output.parent.mkdir(parents=True, exist_ok=True)
    # Use cwd=subtitle parent to avoid path escaping issues in FFmpeg filter syntax.
    command = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-y",
               "-i", str(video.resolve()), "-vf", f"subtitles={subtitles.name}",
               "-map", "0:v:0", "-map", "0:a?", "-c:v", "libx264", "-preset", "veryfast",
               "-crf", "21", "-pix_fmt", "yuv420p", "-c:a", "copy",
               "-movflags", "+faststart", str(output.resolve())]
    subprocess.run(command, cwd=str(subtitles.resolve().parent), check=True, timeout=900)
    if not output.is_file() or output.stat().st_size == 0:
        raise RuntimeError("Caption render failed")
    return {"output": str(output), "captions": str(subtitles)}

def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--video", type=Path, required=True)
    p.add_argument("--srt", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    print(json.dumps(caption(args.video, args.srt, args.output), indent=2))

if __name__ == "__main__":
    main()
