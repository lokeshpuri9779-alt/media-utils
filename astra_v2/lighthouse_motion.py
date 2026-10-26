#!/usr/bin/env python3
"""Opt-in lighthouse-tested camera-motion backend for ASTRA.

Applies a subtle deterministic Ken Burns move to an existing licensed image.
Not AI-generated video, physical wave simulation, or character animation.
Never called by production unless explicitly selected.
"""
from __future__ import annotations
import argparse
import shutil
import subprocess
from pathlib import Path

def render(image: Path, output: Path, *, seconds: float = 4.0, fps: int = 24,
           width: int = 720, height: int = 1280, zoom: float = 1.06) -> None:
    image=image.expanduser().resolve()
    output=output.expanduser().resolve()
    if not image.is_file():
        raise ValueError("Input image missing")
    if not (0.5 <= seconds <= 60 and 1 <= fps <= 60):
        raise ValueError("Invalid duration or FPS")
    if width < 64 or height < 64 or width % 2 or height % 2:
        raise ValueError("Dimensions must be even and at least 64")
    if not 1.0 <= zoom <= 1.25:
        raise ValueError("Zoom must be 1.0..1.25")
    ffmpeg=shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("FFmpeg is required")
    frames=round(seconds*fps)
    # Fit with overscan first, then pan/zoom smoothly; keep the subject source fixed.
    z=f"1+({zoom-1:.6f})*on/{max(1,frames-1)}"
    vf=(f"scale={width*2}:{height*2}:force_original_aspect_ratio=increase,"
        f"crop={width*2}:{height*2},"
        f"zoompan=z='{z}':x='(iw-iw/zoom)/2':y='(ih-ih/zoom)/2':"
        f"d={frames}:s={width}x{height}:fps={fps},"
        f"format=yuv420p")
    output.parent.mkdir(parents=True,exist_ok=True)
    cmd=[ffmpeg,"-hide_banner","-loglevel","error","-y","-loop","1",
         "-i",str(image),"-vf",vf,"-frames:v",str(frames),
         "-an","-c:v","libx264","-pix_fmt","yuv420p",str(output)]
    subprocess.run(cmd,check=True,timeout=600)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--image",required=True,type=Path)
    p.add_argument("--output",required=True,type=Path)
    p.add_argument("--seconds",type=float,default=4)
    p.add_argument("--fps",type=int,default=24)
    a=p.parse_args()
    render(a.image,a.output,seconds=a.seconds,fps=a.fps)
if __name__=="__main__":main()
