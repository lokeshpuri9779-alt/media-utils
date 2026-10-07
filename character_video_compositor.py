from __future__ import annotations

"""Compose generated visuals against the measured character-dialogue master."""

import math
import subprocess
import tempfile
import wave
from pathlib import Path

from imageio_ffmpeg import get_ffmpeg_exe, read_frames


def _run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)


def _measure_output(path: Path, ffmpeg: str) -> dict:
    """Decode the actual streams; never use requested durations as QA evidence."""
    reader = read_frames(str(path))
    try:
        metadata = next(reader)
    finally:
        reader.close()
    video = subprocess.run([
        ffmpeg, "-v", "error", "-i", str(path), "-map", "0:v:0",
        "-an", "-progress", "pipe:1", "-nostats", "-f", "null", "-",
    ], check=True, capture_output=True, text=True)
    frames = [int(line.split("=", 1)[1]) for line in video.stdout.splitlines()
              if line.startswith("frame=")]
    if not frames or frames[-1] <= 0 or not metadata.get("fps"):
        raise RuntimeError("Final character video has no decodable frames.")
    audio = subprocess.run([
        ffmpeg, "-v", "error", "-i", str(path), "-map", "0:a:0",
        "-vn", "-ac", "1", "-ar", "48000", "-f", "s16le", "pipe:1",
    ], check=True, capture_output=True)
    if not audio.stdout:
        raise RuntimeError("Final character video has no decodable audio.")
    return {
        "duration": frames[-1] / float(metadata["fps"]),
        "audio_duration": len(audio.stdout) / (48000 * 2),
        "resolution": list(metadata["size"]),
        "fps": float(metadata["fps"]),
        "frame_count": frames[-1],
    }


def compose_character_short(
    clips: list[Path],
    scene_durations: list[float],
    audio_path: Path,
    output_path: Path,
    width: int = 1080,
    height: int = 1920,
    fps: int = 30,
) -> dict:
    if len(clips) != len(scene_durations) or not clips:
        raise ValueError("Character clips and scene durations must be non-empty and aligned.")
    if fps <= 0 or any(not math.isfinite(d) or d <= 0 for d in scene_durations):
        raise ValueError("Scene durations and frame rate must be positive and finite.")
    with wave.open(str(audio_path), "rb") as master:
        master_duration = master.getnframes() / master.getframerate()
    planned_duration = sum(scene_durations)
    if abs(master_duration - planned_duration) > .04:
        raise RuntimeError("Dialogue master does not match the planned scene timeline.")

    ffmpeg = get_ffmpeg_exe()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cumulative = 0.0
    previous_frame = 0
    boundaries = []

    with tempfile.TemporaryDirectory(prefix="astra_character_compose_") as td:
        td = Path(td)
        normalized = []
        for i, (clip, duration) in enumerate(zip(clips, scene_durations), start=1):
            cumulative += duration
            end_frame = round(cumulative * fps)
            frame_count = end_frame - previous_frame
            if frame_count < 1:
                raise ValueError("A scene is shorter than one output frame.")
            boundaries.append(end_frame / fps)
            previous_frame = end_frame
            dst = td / f"scene_{i:02d}.mp4"
            # Use cumulative frame boundaries to prevent rounding drift at cuts.
            # Hold the final pose if Agnes returns a slightly shorter clip.
            # Always use the dialogue master; generated audio has no timing contract.
            vf = (
                f"setpts=PTS-STARTPTS,"
                f"scale={width}:{height}:force_original_aspect_ratio=increase,"
                f"crop={width}:{height},fps={fps},"
                f"tpad=stop_mode=clone:stop_duration={duration + 1:.6f},"
                "format=yuv420p"
            )
            _run([
                ffmpeg, "-hide_banner", "-loglevel", "error", "-y",
                "-i", str(clip), "-map", "0:v:0", "-an",
                "-vf", vf, "-frames:v", str(frame_count),
                "-c:v", "libx264", "-preset", "fast", "-crf", "18",
                "-pix_fmt", "yuv420p", str(dst),
            ])
            normalized.append(dst)

        manifest = td / "concat.txt"
        manifest.write_text(
            "\n".join(f"file '{p.as_posix()}'" for p in normalized) + "\n",
            encoding="utf-8",
        )
        silent = td / "visual.mp4"
        _run([
            ffmpeg, "-hide_banner", "-loglevel", "error", "-y",
            "-f", "concat", "-safe", "0", "-i", str(manifest),
            "-c", "copy", str(silent),
        ])
        _run([
            ffmpeg, "-hide_banner", "-loglevel", "error", "-y",
            "-i", str(silent), "-i", str(audio_path),
            "-map", "0:v:0", "-map", "1:a:0",
            "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
            "-af", "loudnorm=I=-14:TP=-1.0:LRA=7",
            "-movflags", "+faststart", str(output_path),
        ])

    measured = _measure_output(output_path, ffmpeg)
    if abs(measured["duration"] - master_duration) > .08:
        raise RuntimeError("Rendered video duration differs from the dialogue master.")
    if abs(measured["audio_duration"] - master_duration) > .08:
        raise RuntimeError("Rendered audio duration differs from the dialogue master.")
    if measured["resolution"] != [width, height]:
        raise RuntimeError("Rendered character video has the wrong resolution.")
    return {
        "renderer": "character-video-compositor-2",
        "scene_count": len(clips),
        **measured,
        "planned_duration": planned_duration,
        "master_audio_duration": master_duration,
        "scene_end_seconds": boundaries,
        "output_bytes": output_path.stat().st_size,
        "audio_mode": "astra-dialogue-master",
        "validation": "decoded-streams",
    }
