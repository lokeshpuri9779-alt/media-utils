from __future__ import annotations

"""Compose generated character clips into Astra's final vertical Short."""

import json
import subprocess
import tempfile
from pathlib import Path

from imageio_ffmpeg import get_ffmpeg_exe


def _run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)


def _has_audio(path: Path) -> bool:
    try:
        probe=subprocess.run([
            "ffprobe","-v","error","-select_streams","a:0",
            "-show_entries","stream=codec_type","-of","csv=p=0",str(path)
        ],check=True,capture_output=True,text=True,timeout=20)
        return probe.stdout.strip()=="audio"
    except Exception:
        return False


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

    ffmpeg = get_ffmpeg_exe()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    native_audio=all(_has_audio(Path(p)) for p in clips)

    with tempfile.TemporaryDirectory(prefix="astra_character_compose_") as td:
        td = Path(td)
        normalized = []
        for i, (clip, duration) in enumerate(zip(clips, scene_durations), start=1):
            dst = td / f"scene_{i:02d}.mp4"
            # Generated character video fills the frame. Crop rather than letterbox
            # so the reference-derived style remains immersive and card-free.
            vf = (
                f"scale={width}:{height}:force_original_aspect_ratio=increase,"
                f"crop={width}:{height},fps={fps},format=yuv420p"
            )
            cmd=[
                ffmpeg, "-hide_banner", "-loglevel", "error", "-y",
                "-stream_loop", "-1", "-i", str(clip),
                "-t", f"{max(.1, float(duration)):.3f}",
                "-vf", vf,
                "-c:v", "libx264", "-preset", "fast", "-crf", "18",
                "-pix_fmt", "yuv420p",
            ]
            if native_audio:
                cmd += ["-map","0:v:0","-map","0:a:0","-c:a","aac","-b:a","192k"]
            else:
                cmd += ["-an"]
            cmd.append(str(dst))
            _run(cmd)
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

        if native_audio:
            _run([
                ffmpeg, "-hide_banner", "-loglevel", "error", "-y",
                "-i", str(silent),
                "-map","0:v:0","-map","0:a:0",
                "-c:v","copy","-c:a","aac","-b:a","192k",
                "-af","loudnorm=I=-14:TP=-1.0:LRA=7",
                "-movflags","+faststart",str(output_path),
            ])
        else:
            _run([
                ffmpeg, "-hide_banner", "-loglevel", "error", "-y",
                "-i", str(silent), "-i", str(audio_path),
                "-map", "0:v:0", "-map", "1:a:0",
                "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                "-af", "loudnorm=I=-14:TP=-1.0:LRA=7",
                "-movflags", "+faststart", "-shortest", str(output_path),
            ])

    if not output_path.is_file() or output_path.stat().st_size <= 0:
        raise RuntimeError("Character compositor produced no final video.")

    return {
        "renderer": "character-video-compositor-1",
        "scene_count": len(clips),
        "resolution": [width, height],
        "fps": fps,
        "duration": round(sum(float(x) for x in scene_durations), 3),
        "output_bytes": output_path.stat().st_size,
        "audio_mode": "agnes-native" if native_audio else "astra-fallback",
    }
