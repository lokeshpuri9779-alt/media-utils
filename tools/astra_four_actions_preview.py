"""Actual Studio 1080x1920 visual comparison of four newly directed motions.

Silent on purpose, uses exactly the normal production frame compositor.
No YouTube upload or credential access.
"""
from pathlib import Path
import json
import subprocess

import numpy as np
from imageio_ffmpeg import get_ffmpeg_exe
from studio_renderer import RATE, W, H, render_frame

FPS = 6
SECONDS = 1.7
SHOTS = (
    ("chase", "CHASE THE ROLLING BALL",
     "The fox chased a ball down the rocky hillside while the rabbit followed.",
     "hill"),
    ("catch", "ONE LAST CATCH",
     "The fox caught the painted ball while the rabbit cheered at the river.",
     "river"),
    ("swim", "ACROSS THE RIVER",
     "The fox and rabbit swam together past the floating lantern.",
     "river"),
    ("sneak", "SNEAK THROUGH THE GARDEN",
     "The fox and rabbit tiptoed quietly past the garden gate.",
     "garden"),
)


def render_motion_preview(path="preview/astra-four-directed-actions.mp4"):
    output=Path(path)
    output.parent.mkdir(parents=True,exist_ok=True)
    command=[get_ffmpeg_exe(),"-hide_banner","-loglevel","error","-y",
             "-f","rawvideo","-pix_fmt","rgb24","-s",f"{W}x{H}",
             "-r",str(FPS),"-i","pipe:0","-c:v","libx264",
             "-preset","ultrafast","-pix_fmt","yuv420p",str(output)]
    proc=subprocess.Popen(command,stdin=subprocess.PIPE)
    manifest=[]
    try:
        for action,headline,speech,location in SHOTS:
            shot={
                "story_cast":("fox","rabbit"),
                "story_subject":"fox",
                "story_action":action,
                "story_environment":location,
                "story_visual_seed":"astra-four-action-preview",
                "story_beat":"build",
                "headline":headline,
                "speech":speech,
                "visual":"story",
                "start":0.0,"end":SECONDS,"duration":SECONDS,
                "voice_start":.06,
                "audio":np.zeros(round(RATE*SECONDS),dtype=np.float32),
                "director_camera":"still",
                "creative_format":"microfiction_cinematic",
                "format_brand":"minimal",
            }
            for frame_index in range(round(FPS*SECONDS)):
                local=frame_index/FPS
                frame=render_frame([shot],local,"fiction",SECONDS)
                proc.stdin.write(frame.tobytes())
            manifest.append({"action":action,"speech":speech,
                             "environment":location})
        proc.stdin.close()
        if proc.wait()!=0:
            raise RuntimeError("Studio four-action preview failed to encode")
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait()
    subprocess.run([get_ffmpeg_exe(),"-v","error","-i",str(output),
                    "-f","null","-"],check=True)
    if output.stat().st_size<15000:
        raise RuntimeError("Studio four-action preview unexpectedly empty")
    (output.parent/"astra-four-directed-actions.json").write_text(
        json.dumps({"actions":manifest,"silent_intentionally":True,
                    "auto_published":False,"renderer":"real Studio compositor"},
                    indent=2),encoding="utf-8")
    print("ASTRA_STUDIO_FOUR_ACTION_MP4_VERIFIED",output.stat().st_size)
    return str(output)


if __name__=="__main__":
    render_motion_preview()
