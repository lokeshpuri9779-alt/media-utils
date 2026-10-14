"""Offline MP4 QA: full Studio picture path, without synthesis or publishing.

Narration samples here are intentional silence; this tests scene visuals,
headlines and caption layout, not the production voice engine.
"""
from __future__ import annotations
from pathlib import Path
import subprocess
import numpy as np
from imageio_ffmpeg import get_ffmpeg_exe
from studio_renderer import render_frame, RATE, W, H

FPS=6
BEATS=(
    ("WHAT IS THAT?", "The fox and rabbit discover a mysterious gift box.", "look"),
    ("WATCH OUT!", "The fox warned the rabbit about the gift box!", "wave"),
    ("TAKE IT HOME", "The fox and rabbit carry the gift box together.", "carry"),
)

def render_studio_duo_preview(path="preview/pillow-studio-composite.mp4"):
    path=Path(path)
    path.parent.mkdir(parents=True,exist_ok=True)
    plan=[]
    cursor=0.0
    for headline,speech,action in BEATS:
        duration=2.3
        plan.append({"headline":headline,"speech":speech,"visual":"story",
                     "story_subject":"fox","story_cast":("fox","rabbit"),
                     "story_action":action,"creative_format":"microfiction_cinematic",
                     "format_brand":"minimal","director_camera":"still",
                     "start":cursor,"end":cursor+duration,"duration":duration,
                     "voice_start":cursor+0.08,
                     "audio":np.zeros(int((duration-.25)*RATE),dtype=np.float32)})
        cursor+=duration
    cmd=[get_ffmpeg_exe(),"-hide_banner","-loglevel","error","-y",
         "-f","rawvideo","-pix_fmt","rgb24","-s",f"{W}x{H}",
         "-r",str(FPS),"-i","-","-c:v","libx264","-preset","ultrafast",
         "-pix_fmt","yuv420p",str(path)]
    proc=subprocess.Popen(cmd,stdin=subprocess.PIPE)
    try:
        for frame_num in range(round(FPS*cursor)):
            frame=render_studio_frame(plan,frame_num/FPS,cursor)
            proc.stdin.write(frame.tobytes())
        proc.stdin.close()
        if proc.wait()!=0:
            raise RuntimeError("Studio visual MP4 encoding failed")
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait()
    subprocess.run([get_ffmpeg_exe(),"-v","error","-i",str(path),
                    "-f","null","-"],check=True)
    if path.stat().st_size<10_000:
        raise RuntimeError("Studio MP4 is unexpectedly empty")
    return str(path)

def render_studio_frame(plan,t,duration):
    return render_frame(plan,t,"fiction",duration)

if __name__=="__main__":
    print(render_studio_duo_preview())
