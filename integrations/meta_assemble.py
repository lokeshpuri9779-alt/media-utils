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
    with tempfile.TemporaryDirectory(prefix="astra_meta_") as temp:
        normalized = []
        for i, path in enumerate(inputs, 1):
            target = Path(temp) / f"scene_{i:03d}.mp4"
            subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-y", "-i", str(path), "-vf", "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=30,format=yuv420p", "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "23", str(target)], check=True, timeout=600)
            normalized.append(target)
        concat = Path(temp) / "clips.txt"
        concat.write_text("".join(f"file '{p.as_posix()}'\\n" for p in normalized), encoding="utf-8")
        # Normalized clips have identical encoding and can be concatenated without re-encoding.
        subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-y", "-f", "concat", "-safe", "0", "-i", str(concat), "-c", "copy", str(output)], check=True, timeout=600)
    if not output.is_file() or output.stat().st_size == 0:
        raise RuntimeError("Assembly produced no video")
    return {"output": str(output), "scenes": len(inputs), "note": "Silent video; mix licensed audio and validate quality before publishing"}

def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--manifest", type=Path, required=True)
    p.add_argument("--clips", type=Path, default=Path("meta_handoff/clips"))
    p.add_argument("--output", type=Path, default=Path("meta_handoff/assembled.mp4"))
    args = p.parse_args()
    print(json.dumps(assemble(args.manifest, args.clips, args.output), indent=2))

if __name__ == "__main__":
    main()
