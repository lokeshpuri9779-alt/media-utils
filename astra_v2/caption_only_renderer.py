"""Caption-only Shorts renderer: local Kokoro narration + timed captions + MP4.

No animation, external media, network calls, or paid APIs are used by this module.
Voice model assets are obtained only through the existing Studio Kokoro cache.
"""
from __future__ import annotations

import argparse
import json
import math
import re
import subprocess
import tempfile
import wave
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from imageio_ffmpeg import get_ffmpeg_exe
from astra_v2.cinematic_caption_visuals import (\n    camera_motion_filter, create_floating_caption, create_scene_plate,\n)\n
WIDTH, HEIGHT, FPS, RATE = 1080, 1920, 30, 24000


def caption_chunks(text: str, max_words: int = 6) -> list[str]:
    """Split narration into readable punctuation-aware caption phrases."""
    words = re.findall(r"\S+", str(text).strip())
    chunks, current = [], []
    for word in words:
        current.append(word)
        terminal = bool(re.search(r"[.!?][\"')\]]*$", word))
        if len(current) >= max_words or (terminal and len(current) >= 3):
            chunks.append(" ".join(current))
            current = []
    if current:
        chunks.append(" ".join(current))
    return chunks


def _fit_speed_to_duration(speed: float, duration_seconds: float,
                              target_seconds: float = 34.0) -> float:
    """Estimate a bounded Kokoro speed correction toward the 28–40s target."""
    if duration_seconds <= 0 or target_seconds <= 0:
        raise ValueError("Audio duration and target must be positive")
    if 28.0 <= duration_seconds <= 40.0:
        return float(speed)
    return max(0.75, min(1.25, float(speed) * duration_seconds / target_seconds))


def _font(size: int):
    candidates = (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
        "C:/Windows/Fonts/Arial.ttf",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    )
    for candidate in candidates:
        if Path(candidate).is_file():
            return ImageFont.truetype(candidate, size)
    return ImageFont.load_default()


def _caption_frame(text: str, output: Path, index: int):
    """Create a restrained caption card; no illustrations or animated scenes."""
    # Solid background and synchronized narration captions only: no branding,
    # decorative labels, CTA overlays, illustrations, or scene imagery.
    image = Image.new("RGB", (WIDTH, HEIGHT), (8, 12, 20))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((74, 755, 1006, 1165), radius=34,
                           fill=(15, 21, 34), outline=(48, 62, 84), width=3)
    font = _font(76)
    words = text.split()
    lines, line = [], ""
    for word in words:
        candidate = (line + " " + word).strip()
        if draw.textbbox((0, 0), candidate, font=font)[2] > 820 and line:
            lines.append(line)
            line = word
        else:
            line = candidate
    if line:
        lines.append(line)
    font_size = getattr(font, "size", 76)
    while len(lines) > 3 and font_size > 48:
        font_size -= 4
        font = _font(font_size)
        lines, line = [], ""
        for word in words:
            candidate = (line + " " + word).strip()
            if draw.textbbox((0, 0), candidate, font=font)[2] > 820 and line:
                lines.append(line)
                line = word
            else:
                line = candidate
        if line:
            lines.append(line)
    if len(lines) > 3:
        raise ValueError("Caption exceeds the safe three-line display limit")
    line_height = font_size + 22
    y = (HEIGHT - sum([line_height] * len(lines))) // 2
    for line in lines:
        box = draw.textbbox((0, 0), line, font=font)
        x = (WIDTH - (box[2] - box[0])) // 2
        draw.text((x + 2, y + 3), line, font=font, fill=(0, 0, 0))
        draw.text((x, y), line, font=font, fill=(250, 252, 255))
        y += line_height
    image.save(output, "PNG", optimize=True)


def _verify_mp4_streams(target: Path) -> None:
    """Decode both required streams; fail if the muxed file lacks audio or video."""
    ffmpeg = get_ffmpeg_exe()
    subprocess.run(
        [ffmpeg, "-v", "error", "-i", str(target),
         "-map", "0:v:0", "-map", "0:a:0", "-f", "null", "-"],
        check=True, capture_output=True, text=True,
    )


def render_caption_video(narration: str, output: str, voice: str = "af_heart",
                         speed: float = 1.04, fps: int = FPS) -> dict:
    """Synthesize each phrase, hold its caption for the exact phrase audio, mux MP4."""
    narration = " ".join(str(narration).split())
    if not narration:
        raise ValueError("Narration is required")
    if not 0.75 <= float(speed) <= 1.25:
        raise ValueError("Voice speed must be between 0.75 and 1.25")
    if int(fps) != FPS:
        raise ValueError("Only 30 fps output is supported")
    # Import lazily so text-only validation/tests do not download or initialize models.
    from studio_renderer import voice_engine
    engine = voice_engine()
    chunks = caption_chunks(narration)
    target = Path(output).expanduser()
    if target.suffix.lower() != ".mp4":
        raise ValueError("Output filename must end in .mp4")
    target.parent.mkdir(parents=True, exist_ok=True)

    from astra_v2.performance_short_contract import (
        MAX_SECONDS, MIN_SECONDS, validate_rendered_duration,
    )

    def synthesize_at(requested_speed: float):
        parts, phrase_durations = [], []
        for phrase in chunks:
            samples, sample_rate = engine.create(
                phrase, voice=voice, speed=float(requested_speed), lang="en-us"
            )
            samples = np.asarray(samples, dtype=np.float32)
            if sample_rate != RATE or not len(samples) or not np.isfinite(samples).all():
                raise RuntimeError("Kokoro returned invalid narration audio")
            peak = float(np.max(np.abs(samples)))
            if peak > 0:
                samples = samples * (0.72 / peak)
            parts.append(samples)
            phrase_durations.append(len(samples) / RATE)
        return parts, phrase_durations

    audio_parts, durations = synthesize_at(float(speed))
    actual_duration = sum(durations) + 0.12 * max(0, len(durations) - 1)
    if not MIN_SECONDS <= actual_duration <= MAX_SECONDS:
        adjusted_speed = _fit_speed_to_duration(float(speed), actual_duration)
        if abs(adjusted_speed - float(speed)) >= 0.01:
            audio_parts, durations = synthesize_at(adjusted_speed)
            speed = adjusted_speed
            actual_duration = sum(durations) + 0.12 * max(0, len(durations) - 1)
    validate_rendered_duration(actual_duration)

    with tempfile.TemporaryDirectory(prefix="astra-caption-") as temp:
        work = Path(temp)
        concat_path = work / "audio.wav"
        silence = np.zeros(int(RATE * 0.12), dtype=np.float32)
        combined = []
        for i, samples in enumerate(audio_parts):
            combined.append(samples)
            if i != len(audio_parts) - 1:
                combined.append(silence)
        pcm = np.concatenate(combined)
        with wave.open(str(concat_path), "wb") as handle:
            handle.setnchannels(1)
            handle.setsampwidth(2)
            handle.setframerate(RATE)
            handle.writeframes((np.clip(pcm, -1, 1) * 32767).astype("<i2").tobytes())

        manifest = []
        cursor = 0.0
        segment_list = work / "video-segments.txt"
        segment_paths = []
        for index, (phrase, duration) in enumerate(zip(chunks, durations)):
            segment_duration = duration + (0.12 if index != len(chunks) - 1 else 0)
            background = work / f"scene-{index:04d}.png"
            caption = work / f"floating-caption-{index:04d}.png"
            segment = work / f"segment-{index:04d}.mp4"
            create_scene_plate(phrase, background, index)
            create_floating_caption(phrase, caption, index)
            manifest.append({"caption": phrase, "start": round(cursor, 3),
                             "end": round(cursor + duration, 3),
                             "visual": "procedural_cinematic_motion",
                             "caption_style": "floating_transparent"})
            cursor += segment_duration
            filter_graph = (
                f"[0:v]{camera_motion_filter(segment_duration, FPS, index % 2 == 1)},"
                f"format=rgba[bg];[bg][1:v]overlay=0:0:shortest=1,"
                f"format=yuv420p[v]"
            )
            segment_command = [
                get_ffmpeg_exe(), "-y",
                "-loop", "1", "-framerate", str(FPS), "-i", str(background),
                "-loop", "1", "-framerate", str(FPS), "-i", str(caption),
                "-filter_complex", filter_graph, "-map", "[v]",
                "-t", f"{segment_duration:.6f}", "-an",
                "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
                "-r", str(FPS), "-pix_fmt", "yuv420p", str(segment),
            ]
            subprocess.run(segment_command, check=True, capture_output=True, text=True)
            if not segment.is_file() or segment.stat().st_size < 1024:
                raise RuntimeError(f"FFmpeg did not produce cinematic segment {index}")
            segment_paths.append(segment)

        with segment_list.open("w", encoding="utf-8") as handle:
            for segment in segment_paths:
                handle.write(f"file '{segment.as_posix()}'\\n")
        command = [
            get_ffmpeg_exe(), "-y", "-f", "concat", "-safe", "0",
            "-i", str(segment_list), "-i", str(concat_path),
            "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy",
            "-c:a", "aac", "-b:a", "160k", "-shortest",
            "-movflags", "+faststart", str(target),
        ]
        ffmpeg = get_ffmpeg_exe()
        subprocess.run(command, check=True, capture_output=True, text=True)
        if not target.is_file() or target.stat().st_size < 1024:
            raise RuntimeError("FFmpeg did not produce a valid MP4 file")
        # Require both streams to decode before marking the MP4 ready for review.
        _verify_mp4_streams(target)
        (target.with_suffix(".captions.json")).write_text(
            json.dumps({"schema_version": 1, "fps": FPS, "duration_seconds": round(cursor, 3),
                        "captions": manifest}, indent=2), encoding="utf-8")
    return {"output": str(target), "duration_seconds": round(cursor, 3),
            "caption_count": len(chunks), "resolution": "1080x1920",
            "voice": voice, "speed": round(float(speed), 3), "quality_check": "passed", "published": False}


def main():
    parser = argparse.ArgumentParser(description="Render narration + captions only")
    parser.add_argument("--script", required=True, help="Text narration")
    parser.add_argument("--output", required=True, help="Destination .mp4")
    parser.add_argument("--voice", default="af_heart")
    parser.add_argument("--speed", type=float, default=1.04)
    args = parser.parse_args()
    print(json.dumps(render_caption_video(args.script, args.output, args.voice, args.speed), indent=2))


if __name__ == "__main__":
    main()
