"""Optional licensed soundtrack mixing for assembled ASTRA videos.

Does not fetch copyrighted music or publish to YouTube.
"""
from __future__ import annotations
import argparse
import json
import shutil
import subprocess
from pathlib import Path

def add_soundtrack(video: Path, audio: Path, output: Path, volume: float = 0.3) -> dict:
    if not (0.0 <= volume <= 2.0):
        raise ValueError("volume must be between 0 and 2")
    if not video.is_file() or not audio.is_file():
        raise FileNotFoundError("Both input video and licensed audio file are required")
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        raise RuntimeError("ffmpeg and ffprobe required")
    output.parent.mkdir(parents=True, exist_ok=True)
    # Keep scene dialogue/effects, duck the licensed music under speech.
    # Both inputs are audio-bearing: meta_assemble adds silence when necessary.
    filter_graph = (
        "[0:a:0]aresample=48000,asetpts=PTS-STARTPTS[voice];"
        f"[1:a:0]aresample=48000,volume={volume},asetpts=PTS-STARTPTS[music];"
        "[music][voice]sidechaincompress=threshold=0.04:ratio=8:attack=20:release=400[ducked];"
        "[voice][ducked]amix=inputs=2:duration=first:dropout_transition=0,"
        "alimiter=limit=0.95[mix]"
    )
    subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-y",
         "-i", str(video), "-stream_loop", "-1", "-i", str(audio),
         "-filter_complex", filter_graph, "-map", "0:v:0", "-map", "[mix]",
         "-c:v", "copy", "-c:a", "aac", "-b:a", "160k", "-shortest",
         "-movflags", "+faststart", str(output)],
        check=True, timeout=600,
    )
    if not output.is_file() or output.stat().st_size == 0:
        raise RuntimeError("Audio mix failed")
    return {"output": str(output), "audio_source": str(audio), "warning": "Confirm soundtrack licensing and listen to final mix before publishing"}

def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--video", type=Path, required=True)
    p.add_argument("--audio", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--volume", type=float, default=0.3)
    args = p.parse_args()
    print(json.dumps(add_soundtrack(args.video, args.audio, args.output, args.volume), indent=2))

if __name__ == "__main__":
    main()
