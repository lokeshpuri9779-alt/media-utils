"""Isolated audiovisual QA for Pillow Engine 1 previews.

Never publishes or substitutes for ASTRA's story-specific Studio renderer.
"""
from __future__ import annotations
import json
import subprocess
from pathlib import Path
from imageio_ffmpeg import get_ffmpeg_exe

def inspect(path: str | Path) -> dict:
    """Decode all frames; fail on broken media. No fake narration or captions."""
    path=Path(path)
    if not path.is_file() or path.stat().st_size < 1000:
        raise ValueError("Missing or empty preview")
    proc=subprocess.run([get_ffmpeg_exe(),"-hide_banner","-v","error",
                         "-i",str(path),"-f","null","-"],
                        capture_output=True,text=True,timeout=120)
    if proc.returncode:
        raise ValueError("Preview cannot be decoded: "+proc.stderr[-500:])
    return {"path":str(path),"bytes":path.stat().st_size,"video_decodes":True,
            "narration_verified":False,"captions_verified":False,
            "story_specific":False,"eligible_for_publication":False}

def save_report(path: str | Path, report: str | Path) -> dict:
    result=inspect(path)
    Path(report).write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    return result
