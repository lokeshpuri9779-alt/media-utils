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
    image = Image.new("RGB", (WIDTH, HEIGHT), (7, 10, 18))
    draw = ImageDraw.Draw(image)
    # Subtle static gradient gives the captions contrast without visual clutter.
    for y in range(HEIGHT):
        shade = int(7 + 8 * y / HEIGHT)
        draw.line((0, y, WIDTH, y), fill=(shade, shade + 2, shade + 8))
    draw.text((72, 130), "RAYVAN", font=_font(28), fill=(145, 158, 180))
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
    line_height = font.size + 22
    y = (HEIGHT - sum([line_height] * len(lines))) // 2
    for line in lines:
        box = draw.textbbox((0, 0), line, font=font)
        x = (WIDTH - (box[2] - box[0])) // 2
        draw.text((x + 2, y + 3), line, font=font, fill=(0, 0, 0))
        draw.text((x, y), line, font=font, fill=(250, 252, 255))
        y += line_height
    draw.text((72, 1770), "FOLLOW FOR MORE STORIES", font=_font(25),
              fill=(132, 148, 172))
    image.save(output, "PNG", optimize=True)


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

    audio_parts, durations = [], []
    for phrase in chunks:
        samples, sample_rate = engine.create(phrase, voice=voice, speed=float(speed), lang="en-us")
        samples = np.asarray(samples, dtype=np.float32)
        if sample_rate != RATE or not len(samples) or not np.isfinite(samples).all():
            raise RuntimeError("Kokoro returned invalid narration audio")
        peak = float(np.max(np.abs(samples)))
        if peak > 0:
            samples = samples * (0.72 / peak)
        audio_parts.append(samples)
        durations.append(len(samples) / RATE)

    actual_duration = sum(durations) + 0.12 * max(0, len(durations) - 1)
    from astra_v2.performance_short_contract import validate_rendered_duration
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
        for index, (phrase, duration) in enumerate(zip(chunks, durations)):
            frame = work / f"caption-{index:04d}.png"
            _caption_frame(phrase, frame, index)
            manifest.append({"caption": phrase, "start": round(cursor, 3),
                             "end": round(cursor + duration, 3)})
            cursor += duration + (0.12 if index != len(chunks) - 1 else 0)

        # One still caption card per phrase, with exact phrase-level audio timing.
        concat_file = work / "frames.txt"
        with concat_file.open("w", encoding="utf-8") as handle:
            for index, item in enumerate(manifest):
                handle.write(f"file '{(work / f'caption-{index:04d}.png').as_posix()}'\\n")
                handle.write(f"duration {durations[index] + (0.12 if index != len(chunks)-1 else 0):.6f}\\n")
            handle.write(f"file '{(work / f'caption-{len(chunks)-1:04d}.png').as_posix()}'\\n")
        command = [
            get_ffmpeg_exe(), "-y", "-f", "concat", "-safe", "0", "-i", str(concat_file),
            "-i", str(concat_path), "-vf", f"fps={FPS},format=yuv420p",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
            "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart",
            str(target),
        ]
        subprocess.run(command, check=True, capture_output=True, text=True)
        (target.with_suffix(".captions.json")).write_text(
            json.dumps({"schema_version": 1, "fps": FPS, "duration_seconds": round(cursor, 3),
                        "captions": manifest}, indent=2), encoding="utf-8")
    return {"output": str(target), "duration_seconds": round(cursor, 3),
            "caption_count": len(chunks), "resolution": "1080x1920",
            "voice": voice, "published": False}


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
