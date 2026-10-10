"""Safely assemble validated Meta-exported scene clips into a vertical MP4.

No automatic publishing. Requires local ffmpeg/ffprobe executables.
"""
from __future__ import annotations
import argparse
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

def probe(path: Path) -> dict:
    result = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,width,height:format=duration", "-of", "json", str(path)], check=True, capture_output=True, text=True, timeout=30)
    return json.loads(result.stdout)

def assemble(manifest: Path, clips: Path, output: Path) -> dict:
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        raise RuntimeError("ffmpeg and ffprobe must be installed")
    data = json.loads(manifest.read_text(encoding="utf-8"))
    scenes = data.get("scenes")
    if not isinstance(scenes, list) or not scenes:
        raise ValueError("manifest requires nonempty scenes")
    inputs = [clips / f"scene_{i:03d}.mp4" for i in range(1, len(scenes)+1)]
    for path in inputs:
        if not path.is_file() or path.stat().st_size == 0:
            raise ValueError(f"Missing/empty scene: {path}")
        metadata = probe(path)
        streams = metadata.get("streams", [])
        if not any(s.get("codec_type") == "video" and s.get("width", 0) > 0 and s.get("height", 0) > 0 for s in streams):
            raise ValueError(f"No valid video stream: {path}")
        duration = float(metadata.get("format", {}).get("duration", 0))
        if not 0.25 <= duration <= 120:
            raise ValueError(f"Unreasonable scene duration: {path}")
    output.parent.mkdir(parents=True, exist_ok=True)
    # Never preserve an old success artifact after a failed direct assembly.
    output.unlink(missing_ok=True)
    with tempfile.TemporaryDirectory(prefix="astra_meta_") as temp:
        normalized = []
        # Normalize audio on every clip so concat preserves dialogue and effects.
        for i, path in enumerate(inputs, 1):
            target = Path(temp) / f"scene_{i:03d}.mp4"
            metadata = probe(path)
            has_audio = any(stream.get("codec_type") == "audio" for stream in metadata.get("streams", []))
            command = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-y", "-i", str(path)]
            if not has_audio:
                command += ["-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=48000"]
            command += ["-map", "0:v:0", "-map", "0:a:0" if has_audio else "1:a:0",
                        "-vf", "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=30,format=yuv420p",
                        "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
                        "-c:a", "aac", "-ar", "48000", "-ac", "2", "-b:a", "160k",
                        "-af", "aresample=async=1:first_pts=0", "-shortest", str(target)]
            subprocess.run(command, check=True, timeout=600)
            normalized.append(target)
        concat = Path(temp) / "clips.txt"
        concat.write_text("".join(f"file '{p.as_posix()}'\n" for p in normalized), encoding="utf-8")
        # Normalized clips have identical encoding and can be concatenated without re-encoding.
        subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-y", "-f", "concat", "-safe", "0", "-i", str(concat), "-c", "copy", str(output)], check=True, timeout=600)
    if not output.is_file() or output.stat().st_size == 0:
        raise RuntimeError("Assembly produced no video")
    # Validate the encoded artifact before exposing it to later stages.
    verified = probe(output)
    video_streams = [stream for stream in verified.get("streams", []) if stream.get("codec_type") == "video"]
    audio_streams = [stream for stream in verified.get("streams", []) if stream.get("codec_type") == "audio"]
    if len(video_streams) != 1 or not audio_streams or video_streams[0].get("width") != 1080 or video_streams[0].get("height") != 1920:
        output.unlink(missing_ok=True)
        raise RuntimeError("Assembled video failed stream validation")
    return {"output": str(output), "scenes": len(inputs), "note": "Scene audio retained where available; silent scenes receive a silent audio track. Validate quality before publishing"}

def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--manifest", type=Path, required=True)
    p.add_argument("--clips", type=Path, default=Path("meta_handoff/clips"))
    p.add_argument("--output", type=Path, default=Path("meta_handoff/assembled.mp4"))
    args = p.parse_args()
    print(json.dumps(assemble(args.manifest, args.clips, args.output), indent=2))

if __name__ == "__main__":
    main()
