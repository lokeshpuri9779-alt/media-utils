"""ASTRA episode timeline schema and deterministic narration/scene alignment.

Review-only: no TTS provider, upload, or external generation is implied.
"""
from __future__ import annotations
import json
from pathlib import Path

def build_timeline(scenes, fps=30):
    if fps not in (24,30):raise ValueError("Unsupported FPS")
    if not scenes:raise ValueError("No scenes")
    out=[]; cursor=0
    for i,s in enumerate(scenes):
        text=str(s.get("narration","")).strip()
        image=str(s.get("image","")).strip()
        frames=s.get("frames")
        if not text or not image:raise ValueError(f"Scene {i} missing narration/image")
        if not isinstance(frames,int) or frames<=0:raise ValueError(f"Scene {i} invalid duration")
        out.append({"scene":i,"image":image,"narration":text,
                    "start_frame":cursor,"end_frame":cursor+frames,
                    "start_seconds":round(cursor/fps,3),
                    "end_seconds":round((cursor+frames)/fps,3),
                    "caption":text,"audio_file":s.get("audio_file")})
        cursor+=frames
    return {"fps":fps,"frames":cursor,"duration_seconds":cursor/fps,
            "scenes":out,"narration_ready":all(x["audio_file"] for x in out),
            "publish":False}

def save_timeline(scenes,path,fps=30):
    timeline=build_timeline(scenes,fps)
    p=Path(path);p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(timeline,indent=2)+"\n")
    return timeline
